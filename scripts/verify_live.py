"""Hosted smoke test using a dedicated test account; never prints secrets.

Set PLATEFUL_API_URL, PLATEFUL_TEST_EMAIL, PLATEFUL_TEST_PASSWORD.
Optional --require-ai checks actual semantic retrieval and Gemini explanation.
"""
import argparse
import os
import uuid
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-ai', action='store_true')
    args = parser.parse_args()
    base = os.environ['PLATEFUL_API_URL'].rstrip('/')
    email = os.environ['PLATEFUL_TEST_EMAIL']
    password = os.environ['PLATEFUL_TEST_PASSWORD']
    plan_id = None
    with httpx.Client(base_url=base, timeout=90) as client:
        def call(method, path, **kwargs):
            r = client.request(method, path, **kwargs)
            if r.is_error:
                raise RuntimeError(f'{method} {path}: HTTP {r.status_code}')
            return r.json() if r.status_code != 204 else None
        assert call('GET','/health')['status'] == 'UP'
        creds = {'email': email, 'password': password}
        registered = client.post('/api/v1/auth/register', json=creds)
        if registered.status_code not in (201,409):
            raise RuntimeError(f'Registration returned HTTP {registered.status_code}')
        auth = call('POST','/api/v1/auth/login',json=creds)
        client.headers['Authorization'] = 'Bearer ' + auth['access_token']
        prefs = {'days':['Monday','Tuesday'],'budget':1000,'people':2,'goals':['protein'],
                 'diet':'vegan','allergies':['dairy'],'appliances':['stove','pressure-cooker'],
                 'meal_types':['dinner'],'pantry_quantities':[{'name':'rice','quantity':300,'unit':'g'}]}
        try:
            call('PUT','/api/v1/users/me/preferences',json=prefs)
            call('PUT','/api/v1/users/me/pantry',json={'items':prefs['pantry_quantities']})
            result = call('POST','/api/v1/plans/generate',json=prefs)
            plan_id = result['id']
            assert result['budget_remaining'] >= 0 and len(result['meals']) == 2
            if args.require_ai:
                assert result['retrieval_mode'] == 'pgvector', 'Semantic retrieval is not active'
                assert result['ai_mode'] == 'gemini', 'Gemini highlights are not active'
            first = result['meals'][0]
            changed = call('POST',f"/api/v1/plans/{plan_id}/items/{first['id']}/swap")
            assert changed['meals'][0]['recipe_id'] != first['recipe_id']
            assert call('POST','/api/v1/plans',json={'plan_id':plan_id})['saved']
            assert any(p['id']==plan_id for p in call('GET','/api/v1/plans'))
            items = call('GET',f'/api/v1/plans/{plan_id}/groceries')
            if items:
                assert call('PATCH',f"/api/v1/plans/{plan_id}/groceries/{items[0]['id']}",json={'checked':True})['checked']
            print('PASS: health, login, preferences, pantry, generation, swap, history and grocery persistence')
            print('Retrieval:',result['retrieval_mode'],'Explanation:',result['ai_mode'])
        finally:
            if plan_id:
                call('DELETE',f'/api/v1/plans/{plan_id}')
            call('POST','/api/v1/auth/logout')
        assert client.get('/api/v1/auth/me').status_code == 401
        print('PASS: test plan cleanup and token revocation')


if __name__ == '__main__':
    main()
