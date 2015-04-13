from pyramid.view import view_config
from lib.wp import SparkUpWP
from pyramid.response import Response


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    return {'project': 'sparkplug'}


@view_config(route_name='socketio')
def socketio(request):
    from socketio import socketio_manage
    socketio_manage(request.environ, {'/sparkupwp': SparkUpWP}, request=request)
    return Response('')