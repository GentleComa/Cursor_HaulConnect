"""
Dispatch Routes

Load management and dispatch operations.
"""

from flask import render_template
from app.dispatch import dispatch_bp


@dispatch_bp.route('/')
def loads():
    """List all available loads."""
    # TODO: Implement loads list
    return render_template('dispatch/loads.html')


@dispatch_bp.route('/load/<int:load_id>')
def load_detail(load_id):
    """View load details."""
    # TODO: Implement load detail
    return render_template('dispatch/load_detail.html', load_id=load_id)


@dispatch_bp.route('/create', methods=['GET', 'POST'])
def create_load():
    """Create new load posting."""
    # TODO: Implement load creation
    return render_template('dispatch/create_load.html')


@dispatch_bp.route('/my-loads')
def my_loads():
    """View user's assigned/posted loads."""
    # TODO: Implement my loads view
    return render_template('dispatch/my_loads.html')

