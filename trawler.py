#!/usr/bin/env python3
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Server
from jsonschema import validate

import base64
import dateutil.parser
import json


# App setup
app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trawler.db'

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Manager/CLI setup
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('debug', Server(use_debugger=True))

# Load JSON schemas
schemas = dict()
schemas['reports'] = json.load(open('schemas/report.schema'))


@app.route('/')
@app.route('/dashboard')
def index():
    return render_template('index.html', reports=Report.query.all())


# Submission portal for phishing reports, only available via API access.
# This currently has no method of authentication/verification, be wary.
@app.route('/report', methods=['POST'])
def report():
    # Get the JSON report and validate it against the schema
    report = request.get_json()
    validate(report, schemas['reports'])

    if report is not None:
        report = Report(report['reporter'], report['report_time'],
                        report['message_id'], report)
        return '', 200
    else:
        return 'No JSON found in request.', 415


tos = db.Table('tos',
               db.Column('email_id', db.Text, db.ForeignKey('email.id')),
               db.Column('email_address', db.Text,
                         db.ForeignKey('email_address.email')))

ccs = db.Table('ccs',
               db.Column('email_id', db.Text, db.ForeignKey('email.id')),
               db.Column('email_address', db.Text,
                         db.ForeignKey('email_address.email')))


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter = db.Column(db.Text)
    report_time = db.Column(db.DateTime)
    email_id = db.Column(db.Text, db.ForeignKey('email.id'))
    email = db.relationship('Email', backref=db.backref('reports',
                                                        lazy='dynamic'))

    def __init__(self, reporter, report_time, email_id, json):
        self.reporter = reporter
        self.report_time = dateutil.parser.parse(report_time)
        self.email_id = email_id

        # Create email if we do not already have it
        if Email.query.get(email_id) is None:
            email = Email(email_id, json['sender'], json['subject'],
                          json['body']['preffered'], json['body']['plaintext'],
                          json['body']['html'], json['body']['rtf'])

            # Add headers
            for index, header in enumerate(json['headers']):
                db.session.add(EmailHeader(email_id, index, header[0],
                                           header[1]))

            # Add recipients (tos and ccs)
            for to in json['tos']:
                # Create address if it does not exist, and then append to tos
                address = EmailAddress.query.get(to)
                if address is None:
                    email.tos.append(EmailAddress(to))
                else:
                    email.tos.append(address)

            for cc in json['ccs']:
                # Create address if it does not exist, and then append to ccs
                address = EmailAddress.query.get(cc)
                if address is None:
                    email.ccs.append(EmailAddress(cc))
                else:
                    email.ccs.append(address)

            # Add attachments
            for attachment in json['attachments']:
                db.session.add(EmailAttachment(email_id,
                                               attachment['filename'],
                                               attachment['mimetype'],
                                               attachment['blob']))

            # Add email to database
            db.session.add(email)

        # Add report to database, and commit all changes
        db.session.add(self)
        db.session.commit()


class Email(db.Model):
    id = db.Column(db.Text, primary_key=True)
    sender = db.Column(db.Text, db.ForeignKey('email_address.email'))
    subject = db.Column(db.Text)
    preffered_body = db.Column(db.Text)
    plaintext_body = db.Column(db.Text)
    html_body = db.Column(db.Text)
    rtf_body = db.Column(db.Text)
    tos = db.relationship('EmailAddress', secondary=tos,
                          backref=db.backref('to_emails', lazy='dynamic'))
    ccs = db.relationship('EmailAddress', secondary=ccs,
                          backref=db.backref('cc_emails', lazy='dynamic'))
    headers = db.relationship('EmailHeader', backref='email', lazy='dynamic')

    def __init__(self, email_id, sender, subject, preffered_body,
                 plaintext_body, html_body, rtf_body):
        self.id = email_id
        self.sender = sender
        self.subject = subject
        self.preffered_body = preffered_body
        self.plaintext_body = plaintext_body
        self.html_body = html_body
        self.rtf_body = rtf_body


class EmailAddress(db.Model):
    email = db.Column(db.Text, primary_key=True)

    def __init__(self, email):
        self.email = email.lower()


class EmailHeader(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Text, db.ForeignKey('email.id'))
    index = db.Column(db.Integer)
    key = db.Column(db.Text)
    value = db.Column(db.Text)

    def __init__(self, email_id, index, key, value):
        self.email_id = email_id
        self.index = index
        self.key = key
        self.value = value


class EmailAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.Text, db.ForeignKey('email.id'))
    filename = db.Column(db.Text)
    mimetype = db.Column(db.Text)
    file = db.Column(db.LargeBinary)

    def __init__(self, email_id, filename, mimetype, file):
        self.email_id = email_id
        self.filename = filename
        self.mimetype = mimetype
        self.file = base64.b64decode(file)


class FileHash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('email_attachment.id'))
    hash_type = db.Column(db.Text)
    hash_value = db.Column(db.LargeBinary)

    def __init__(self, file_id, hash_type, hash_value):
        self.file_id = file_id
        self.hash_type = hash_type
        self.hash_value = hash_value


if __name__ == '__main__':
    manager.run()
