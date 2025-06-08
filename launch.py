import sys

from speedoflight.application import SolApplication

app = SolApplication()
exit_code = app.run()
sys.exit(exit_code)
