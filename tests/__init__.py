from copy import deepcopy


class MockRequest:

    def __init__(self, data=None, method='GET', remote_address='127.0.0.1'):
        self.method = method
        self.META = {}

        if method == 'GET':
            self.GET = deepcopy(data) or {}
        elif method == 'POST':
            self.POST = deepcopy(data) or {}

        # Most tests use unproxied requests, the case of proxied ones
        # is unit-tested by the `test_get_origin_ip_address` method.
        if remote_address is not None:
            self.META['REMOTE_ADDR'] = remote_address
