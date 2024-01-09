import re
import ssl

import requests

from tests.tests_deployment import constants


def get_jupyterhub_session():
    session = requests.Session()
    r = session.get(
        f"https://{constants.NEBARI_HOSTNAME}/hub/oauth_login", verify=False
    )
    auth_url = re.search('action="([^"]+)"', r.content.decode("utf8")).group(1)

    r = session.post(
        auth_url.replace("&amp;", "&"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": constants.KEYCLOAK_USERNAME,
            "password": constants.KEYCLOAK_PASSWORD,
            "credentialId": "",
        },
        verify=False,
    )
    xsrf_token_pattern = re.compile(rb'xsrf_token:\s*"([^"]+)"')
    # Search for the pattern in the code
    xsrf_token_search = xsrf_token_pattern.search(r.content)
    xsrf_token = None
    if xsrf_token_search:
        xsrf_token = xsrf_token_pattern.search(r.content).group(1).decode()
    print("*"*100)
    print(f"r.headers: {r.headers}")
    print(f"r.content: {r.content}")
    return session, xsrf_token


def get_jupyterhub_token(note="jupyterhub-tests-deployment"):
    session, xsrf_token = get_jupyterhub_session()
    r = session.post(
        f"https://{constants.NEBARI_HOSTNAME}/hub/api/users/{constants.KEYCLOAK_USERNAME}/tokens?_xsrf={xsrf_token}",
        headers={
            "Referer": f"https://{constants.NEBARI_HOSTNAME}/hub/token",
        },
        json={
            "note": note,
            "expires_in": None,
        },
    )
    print(f"get_jupyterhub_token response: {r}, {r.content}")
    return r.json()["token"]


def monkeypatch_ssl_context():
    """
    This is a workaround monkeypatch to disable ssl checking to avoid SSL
    failures.
    TODO: A better way to do this would be adding the Traefik's default certificate's
    CA public key to the trusted certificate authorities.
    """

    def create_default_context(context):
        def _inner(*args, **kwargs):
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

        return _inner

    sslcontext = ssl.create_default_context()
    ssl.create_default_context = create_default_context(sslcontext)
