Install
=======

    mkdir xsn-sonos-dev
    cd xsn-sonos-dev
    git clone http://github.com/cato-/xsn-sonos.git
    virtualenv --system-site-packages venv
    source venv/bin/activate
    cd xsn-sonos
    pip install -r reqirements.txt

Run and Devel
=============

    cd xsn-sonos-dev/xsn-sonos
    export DJANGO_SETTINGS_MODULE=xsn.settings
    python -m sonos.xml

Make changes in venv/src/django-radioportal-sonos*/sonos/xml.py

venv/src/django-radioportal-sonos* is a separate git repository.
