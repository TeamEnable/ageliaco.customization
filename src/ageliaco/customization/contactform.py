# -*- coding: utf-8 -*-

from Acquisition import aq_inner
from plone.formwidget.recaptcha.widget import ReCaptchaFieldWidget
from plone.schema import email
from plone.app.users.schema import checkEmailAddress
from plone.z3cform.layout import wrap_form
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import interface
from zope import schema
from zope.component import getMultiAdapter

import logging


logger = logging.getLogger(__name__)


class IReCaptchaForm(interface.Interface):
    name = schema.TextLine(title=u"Nom complet", description=u"Veuiller saisir votre nom complet.", required=True)
    email = email.Email(title=u"Expéditeur", description=u"Veuiller saisir votre adresse email.",
                        required=True,
                        constraint=checkEmailAddress)
    subject = schema.TextLine(title=u"Sujet", description=u"", required=True)
    message = schema.Text(title=u"Message", description=u"", required=False)
    captcha = schema.TextLine(title=u"ReCaptcha", description=u"", required=False)


class ReCaptcha(object):
    name = ""
    email = ""
    subject = ""
    message = ""
    captcha = ""

    def __init__(self, context):
        self.context = context


class BaseForm(form.Form):
    """ example captcha form """

    fields = field.Fields(IReCaptchaForm)
    fields["captcha"].widgetFactory = ReCaptchaFieldWidget

    @button.buttonAndHandler(u"Save")
    def handleApply(self, action):
        data, errors = self.extractData()
        captcha = getMultiAdapter(
            (aq_inner(self.context), self.request), name="recaptcha"
        )
        print(data)

        if captcha.verify():
            logger.info("ReCaptcha validation passed.")

            mailhost = self.context.MailHost
            dest_email = self.context.getProperty('email_from_address')  # "kamon.ayeva@gmail.com"
            send_email = self.context.getProperty('email_from_address')  # "support@ageliaco.org"

            try:
                mailhost.send(f"Message de {data['name']} ({data['email']}) : {data['message']}",
                              dest_email,
                              send_email,
                              data["subject"])
                logger.info("Message emailed.")
            except Exception:
                logger.error(f"SMTP exception while trying to send an email to {dest_email}")
        else:
            logger.info("The code you entered was wrong, please enter the new one.")
            return


ReCaptchaForm = wrap_form(BaseForm)
