from datetime import datetime,timedelta,timezone
import jwt
from unittest.mock import patch
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import User
from app.core.config import settings


def test_health_and_cors(client):
    assert client.get('/health').json()=={'status':'UP'}
    response=client.options('/api/v1/plans/generate',headers={'Origin':'http://localhost:5500','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'})
    assert response.headers['access-control-allow-origin']=='http://localhost:5500'
    assert client.options('/api/v1/plans/generate',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST'}).status_code==400


def test_complete_account_plan_flow(client,authorized,preferences):
    assert client.get('/api/v1/auth/me',headers=authorized).status_code==200
    assert client.put('/api/v1/users/me/preferences',headers=authorized,json=preferences).status_code==200
    assert client.get('/api/v1/users/me/preferences',headers=authorized).json()['diet']=='vegan'
    pantry={'items':[{'name':'rice','quantity':.5,'unit':'kg'}]}
    assert client.put('/api/v1/users/me/pantry',headers=authorized,json=pantry).status_code==200
    preferences['pantry_quantities']=pantry['items']
    response=client.post('/api/v1/plans/generate',headers=authorized,json=preferences)
    assert response.status_code==200,response.text
    plan=response.json();plan_id=plan['id']
    assert plan['retrieval_mode'].startswith('deterministic')
    assert plan['budget_remaining']>=0
    assert client.get('/api/v1/plans',headers=authorized).json()==[]
    assert client.post('/api/v1/plans',headers=authorized,json={'plan_id':plan_id}).json()['saved']
    assert len(client.get('/api/v1/plans',headers=authorized).json())==1
    assert client.get('/api/v1/plans/'+plan_id,headers=authorized).json()['id']==plan_id
    item=plan['meals'][0]
    swapped=client.post(f"/api/v1/plans/{plan_id}/items/{item['id']}/swap",headers=authorized)
    assert swapped.status_code==200,swapped.text
    assert swapped.json()['meals'][0]['recipe_id']!=item['recipe_id']
    groceries=client.get(f'/api/v1/plans/{plan_id}/groceries',headers=authorized).json()
    assert client.patch(f"/api/v1/plans/{plan_id}/groceries/{groceries[0]['id']}",headers=authorized,json={'checked':True}).json()['checked']
    assert client.delete('/api/v1/plans/'+plan_id,headers=authorized).status_code==204
    assert client.get('/api/v1/plans/'+plan_id,headers=authorized).status_code==404


def test_auth_password_logout_and_jwt(client,authorized,preferences):
    with Session(engine()) as db:
        user=db.scalar(select(User));assert user.password_hash.startswith('$argon2')
    creds={'email':'one@example.com','password':'a-secure-test-password'}
    login=client.post('/api/v1/auth/login',json=creds)
    assert login.status_code==200
    assert client.post('/api/v1/auth/login',json=creds|{'password':'wrong-password-string'}).status_code==401
    assert client.post('/api/v1/plans/generate',json=preferences).status_code==401
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer bad-token'}).status_code==401
    claims=jwt.decode(login.json()['access_token'],options={'verify_signature':False})
    claims['exp']=datetime.now(timezone.utc)-timedelta(minutes=1)
    expired=jwt.encode(claims,settings().jwt_secret,algorithm='HS256')
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+expired}).status_code==401
    assert client.post('/api/v1/auth/logout',headers=authorized).status_code==204
    assert client.get('/api/v1/auth/me',headers=authorized).status_code==401


def test_owner_isolation(client,authorized,preferences):
    plan=client.post('/api/v1/plans/generate',headers=authorized,json=preferences).json()
    other=client.post('/api/v1/auth/register',json={'email':'two@example.com','password':'another-long-password'}).json()
    headers={'Authorization':'Bearer '+other['access_token']}
    for method,path,body in [('get','/plans/'+plan['id'],None),('delete','/plans/'+plan['id'],None),('post','/plans',{'plan_id':plan['id']}),('post',f"/plans/{plan['id']}/items/{plan['meals'][0]['id']}/swap",None),('get',f"/plans/{plan['id']}/groceries",None)]:
        assert client.request(method,'/api/v1'+path,headers=headers,**({'json':body} if body else {})).status_code==404


def test_validation_and_request_limit(client,authorized,preferences):
    response=client.post('/api/v1/plans/generate',headers=authorized,json=preferences|{'people':0})
    assert response.status_code==422
    assert 'request_id' in response.json()['error']
    assert client.post('/api/v1/plans/generate',headers=authorized,content='x'*65537).status_code==413
    assert client.post('/api/v1/plans/generate',headers=authorized,json=preferences|{'budget':1}).json()['error']['code']=='budget_infeasible'


def test_rate_limit(client,monkeypatch):
    monkeypatch.setattr(settings(),'rate_limit_per_minute',1)
    creds={'email':'nobody@example.com','password':'wrong-password-string'}
    assert client.post('/api/v1/auth/login',json=creds).status_code==401
    assert client.post('/api/v1/auth/login',json=creds).status_code==429


def test_account_management(client, authorized):
    me = client.get('/api/v1/auth/me', headers=authorized).json()
    assert not me['email_verified']
    
    # Email verification
    with patch('app.api.auth.send_email') as mock_send:
        send_verify = client.post('/api/v1/auth/send-verification', headers=authorized)
        assert send_verify.status_code == 200
        text_body = mock_send.call_args.kwargs['text_body']
        token = text_body.split('verify_token=')[1].strip()
    assert token
    
    verify = client.post('/api/v1/auth/verify-email', json={'token': token})
    assert verify.status_code == 200
    
    # Verify token cannot be reused
    reuse_verify = client.post('/api/v1/auth/verify-email', json={'token': token})
    assert reuse_verify.status_code == 400
    assert 'expired or was already used' in reuse_verify.json()['error']['message']
    
    me = client.get('/api/v1/auth/me', headers=authorized).json()
    assert me['email_verified']
    
    # Password reset
    with patch('app.api.auth.send_email') as mock_send:
        req_reset = client.post('/api/v1/auth/request-password-reset', json={'email': me['email']})
        assert req_reset.status_code == 200
        text_body = mock_send.call_args.kwargs['text_body']
        reset_token = text_body.split('reset_token=')[1].strip()
    assert reset_token
    
    new_password = 'new-secure-password-123'
    reset = client.post('/api/v1/auth/reset-password', json={'token': reset_token, 'new_password': new_password})
    assert reset.status_code == 200
    
    # Verify token cannot be reused
    reuse = client.post('/api/v1/auth/reset-password', json={'token': reset_token, 'new_password': 'another-password-456'})
    assert reuse.status_code == 400
    assert 'expired or was already used' in reuse.json()['error']['message']
    
    # Old token is revoked
    assert client.get('/api/v1/auth/me', headers=authorized).status_code == 401
    
    # Login with new password
    login = client.post('/api/v1/auth/login', json={'email': me['email'], 'password': new_password})
    assert login.status_code == 200
    new_auth = {'Authorization': 'Bearer ' + login.json()['access_token']}
    
    # Account deletion
    assert client.delete('/api/v1/auth/account', headers=new_auth).status_code == 204
    assert client.get('/api/v1/auth/me', headers=new_auth).status_code == 401
    assert client.post('/api/v1/auth/login', json={'email': me['email'], 'password': new_password}).status_code == 401

