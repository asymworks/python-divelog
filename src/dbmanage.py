#!/usr/bin/env python
from migrate.versioning.shell import main
main(debug='False', repository='divelog/db/migrations')
