
from flask import url_for, request, session, jsonify, abort
from flask_oauthlib.client import OAuth


def create_client(app, name, **kwargs):
    """
    Helper function to create a OAuth2 client to test an OAuth2 provider.
    """
    default = dict(
        consumer_key='dev',
        consumer_secret='dev',
        request_token_params={'scope': 'user'},
        base_url=app.config['CFG_SITE_SECURE_URL'],
        request_token_url=None,
        access_token_method='POST',
        access_token_url='%s/oauth/token' % app.config['CFG_SITE_SECURE_URL'],
        authorize_url='%s/oauth/authorize' % app.config['CFG_SITE_SECURE_URL'],
    )
    default.update(kwargs)

    oauth = OAuth(app)
    remote = oauth.remote_app(name, **default)

    @app.route('/oauth2test/login')
    def login():
        return remote.authorize(callback=url_for('authorized', _external=True))

    @app.route('/oauth2test/logout')
    def logout():
        session.pop('dev_token', None)
        return "logout"

    @app.route('/oauth2test/authorized')
    @remote.authorized_handler
    def authorized(resp):
        if resp is None:
            return 'Access denied: error=%s' % (
                request.args.get('error', "unknown")
            )
        if isinstance(resp, dict) and 'access_token' in resp:
            session['dev_token'] = (resp['access_token'], '')
            return jsonify(resp)
        return str(resp)

    def get_test(test_url):
        if 'dev_token' not in session:
            abort(403)
        else:
            ret = remote.get(test_url)
            if ret.status != 200:
                return abort(ret.status)
            return ret.raw_data

    @app.route('/oauth2test/test-ping')
    def test_ping():
        return get_test("/oauth/ping")

    @app.route('/oauth2test/test-info')
    def test_info():
        return get_test("/oauth/info")

    @app.route('/oauth2test/test-invalid')
    def test_invalid():
        return get_test("/oauth/invalid")

    @remote.tokengetter
    def get_oauth_token():
        return session.get('dev_token')

    return remote
