Knighted
========


Knighted, is heavily inspired by jeni_ and works only with asyncio_.
It allows to described dependencies, and inject them later.

For example::

    from knighted import annotation, Injector

    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('bar')
    def bar_factory():
        return 'I am bar'

    @services.factory('all')
    def together_factory():
        foo = yield from services.get('foo')
        bar = yield from services.get('bar')
        return [foo, bar]

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (yield from services.apply(fun)) == {'foo': 'I am foo',
                                                 'bar': 'I am bar'}

.. _asyncio: https://pypi.python.org/pypi/asyncio
.. _jeni: https://pypi.python.org/pypi/jeni
