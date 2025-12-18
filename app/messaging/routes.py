"""
Messaging Routes

Internal messaging system routes.
"""

from flask import render_template
from app.messaging import messaging_bp


@messaging_bp.route('/')
def inbox():
    """User message inbox."""
    # TODO: Implement inbox
    return render_template('messaging/inbox.html')


@messaging_bp.route('/compose')
def compose():
    """Compose new message."""
    # TODO: Implement compose
    return render_template('messaging/compose.html')


@messaging_bp.route('/thread/<int:thread_id>')
def thread(thread_id):
    """View message thread."""
    # TODO: Implement thread view
    return render_template('messaging/thread.html', thread_id=thread_id)

