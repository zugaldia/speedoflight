import asyncio
import sys

# Requires PyGObject>=3.50
from gi.events import GLibEventLoopPolicy

from speedoflight.application import SolApplication

# Integrates PyGObject with Python's asyncio
# https://pygobject.gnome.org/guide/asynchronous.html#asynchronous-programming-with-asyncio
policy = GLibEventLoopPolicy()
asyncio.set_event_loop_policy(policy)

app = SolApplication()
exit_code = app.run(sys.argv)
sys.exit(exit_code)
