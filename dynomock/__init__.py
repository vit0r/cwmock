"""init imports for use in main file"""

from hashlib import md5
from os import environ
from pathlib import Path

import click
from tinymongo import TinyMongoClient
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

__all__ = click


class DynoMock:
    """
    Create dynamics mocks for urls
    """
    def __init__(self):
        """

        """
        self.content_type = None
        self.status_code = 200
        self.url_map = Map([Rule('/dynomocklib/update/')])
        self.url_map.strict_slashes = False
        self.mock_path = Path('mocks')

    @property
    def error_404(self):
        """

        :return:
        """
        return 404

    def get_mock_from_db(self, mock_id):
        """
        Get data from tinymongo
        :param mock_id: mock id md5
        :return:
        """
        mocks_db = self.get_db()
        query = {'_id': mock_id}
        mock_db = mocks_db.mocks.find_one(query)
        return mock_db

    def result(self, response):
        """
        Create mock response for http
        :param response:
        :return:
        """
        return Response(
            response=response.get('data'),
            status=self.status_code,
            content_type=response.get('content_type'),
        )

    @classmethod
    def build_mock(cls, request):
        """

        :param request:
        :return:
        """
        new_data = {
            'content_type': request.content_type if request.content_type else 'application/json',
            'path': request.url,
            'query_string': request.query_string.decode('utf-8'),
            'data': request.data.decode('utf-8'),
            'method': request.method
        }
        request_bytes = str(new_data).strip().encode('utf-8')
        mock_id = md5(request_bytes).hexdigest()
        return mock_id, new_data

    def get_mocks_dir(self):
        """

        :return:
        """
        mocks_dir = Path(environ.get('APPLICATION_ROOT_MOCKS', self.mock_path))
        if not Path.exists(mocks_dir):
            Path.mkdir(mocks_dir, parents=True)
        return mocks_dir

    def get_db(self):
        """

        :return:
        """
        connection = TinyMongoClient(foldername=self.mock_path.resolve())
        mock_db = connection.mocks
        collection = mock_db.apis
        return collection

    def create_mock(self, mock, mock_id):
        """

        :param mock:
        :param mock_id:
        :return:
        """
        mock['_id'] = mock_id
        data_id = self.get_db().insert_one(mock).inserted_id
        if data_id:
            return mock_id, mock
        return None

    def dispatch_request(self, request):
        """

        :param request:
        :return:
        """
        #adapter = self.map_requested_url(request)
        print('request: ', request)

        mock_id, mock_data = self.build_mock(request)
        print('Mock id:', mock_id)
        print('Mock info:\n', mock_data)
        if not mock_data.get('data'):
            put_url = 'PUT - http://localhost:5001/dynomock/update/{}'
            print('Create mock id: {} on: {}'.format(mock_id, put_url))
        mock_from_db = self.get_mock_from_db(mock_id)
        if mock_from_db:
            return self.result(mock_from_db)
        mock_id, mock_data = self.create_mock(mock_data, mock_id)
        return self.result(mock_data)

    """def map_requested_url(self, request):
        if Rule(request.path) not in self.url_map._rules:
            self.url_map.add([Rule(request.path)])
        adapter = self.url_map.bind_to_environ(request.environ)
        adapter.match() # check if url was mapped
        return adapter
    """

    def wsgi_app(self, request_environ, start_response):
        """
        make response wsgi
        :param request_environ:
        :param start_response:
        :return:
        """
        request = Request(request_environ)
        response = self.dispatch_request(request)
        return response(request_environ, start_response)

    def __call__(self, request_environ, start_response):
        """
        call request dispatcher
        :param request_environ:
        :param start_response:
        :return:
        """
        return self.wsgi_app(request_environ, start_response)
