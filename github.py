#!/usr/bin/python
import fire
import os
import re
import requests
from configparser import ConfigParser
from datetime import datetime


HTTP_OK_200 = 200
HTTP_CREATED_201 = 201
HTTP_AUTHORIZATION_401 = 401
HTTP_NOT_FOUND_404 = 404


class Github(object):
    '''Base class to interface with Github.com.
    '''
    username = os.environ.get('GITHUB_USERNAME')
    token = os.environ.get('GITHUB_TOKEN')

    class Checks(object):
        '''Abstraction of PR checks.
        '''
        def _request(self, method, path, payload=None, expected_status=None):
            '''RFC2617 defined Basic Authentication via HTTP/token.
            '''
            client = Github()
            url = client.info()['url']
            response = method(
                '%s%s' % (url, path),
                headers={
                    'Accept': 'application/vnd.github.antiope-preview+json',
                    'Authorization': '%s:%s' % (client.username, client.token)
                }
            )

            # Validate potential responses
            if response.status_code in (HTTP_AUTHORIZATION_401, HTTP_NOT_FOUND_404):
                raise Exception('Invalid credentials provided for auth')

            # Validate expected status codes for a give action
            if expected_status is None:
                expected_status = (HTTP_OK_200, )
            elif isinstance(expected_status, int):
                expected_status = (expected_status, )

            if response.status_code not in expected_status:
                raise Exception('Unexpected response [%s] for `%s`' % (response.status_code, path))

            return response

        def create(self, name, branch, sha):
            '''Create new checks for a given commit.
            '''
            response = self._request(
                requests.post,
                '/check-runs',
                payload={
                    'name': name,
                    'branch': branch,
                    'head_sha': sha,
                    'status': 'completed',
                    'conclusion': 'success',
                    'completed_at': datetime.now().isoformat()
                },
                expected_status=(HTTP_CREATED_201, )
            )
            return response.json

        def list(self, commit_hash):
            '''Lists the checks for a given commit.
            '''
            response = self._request(
                requests.get,
                '/commits/%s/check-runs' % commit_hash
            )
            return response.json

    @staticmethod
    def info():
        '''Returns info about the current repository.
        '''
        info = {}
        config = ConfigParser()
        config.read('.git/config')

        # Validate that this is hosted on remote
        try:
            remote_url = config['remote "origin"']['url']
        except KeyError:
            raise ValueError('Git repository does not have remote origin')

        # Retrieve the information we need
        m = re.match(
            r'git@(?P<host>github\.com):(?P<username>[a-zA-Z0-9]+)/(?P<repo_name>[a-zA-Z0-9_-]+)\.git',
            remote_url
        )

        # Validate that the repo is on Github
        if m.group('host') is None:
            raise ValueError('Git repository origin is not Github.com')

        # Build the URL
        info['url'] = 'https://api.github.com/repos/%(owner)s/%(repo)s' % {
            'owner': m.group('username'),
            'repo': m.group('repo_name'),
        }

        # Determine where is the HEAD
        with open('.git/HEAD') as file:
            m = re.match(r'ref: ref/heads/(?P<branch>[a-zA-Z0-9_-]+)', f.read())
            if m.group('branch') is None:
                raise ValueError('Unable to find current branch name')
            info['branch'] = m.group('branch')

        return info


if __name__ == '__main__':
    fire.Fire(Github)
