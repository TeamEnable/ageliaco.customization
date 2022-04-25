# -*- coding: utf-8 -*-

from Products.Five.browser import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides
from Products.PlonePAS.permissions import ManageGroups
from plone import api

import csv
# from io import StringIO
import logging
import random

logger = logging.getLogger(__name__)


MEMBERFIELDS = [
    # "user_id",
    "email", "fullname", "description",
    "location", "cotisation_2021", "cotisation_2022",
    #"test", "fonction",
]


class MemberListView(BrowserView):
    """Members listing"""

    def table_columns(self):
        exclude_memberIds = ["portal_skin","listed","login_time","last_login_time","error_log_update","language","ext_editor","wysiwyg_editor","visible_ids","home_page","location"]
        results = []

        memberIds = self.context.portal_memberdata.propertyIds()

        for id in memberIds:
            if id not in exclude_memberIds:
                results.append(id)

        return results

    def members(self):
        # results = []
        users = api.user.get_users()

        return users


class MemberExportView(BrowserView):
    """Members export"""

    def __call__(self):
        request = self.context.REQUEST

        # Cette partie du code génère le fichier MEMBERS.CSV quise trouve dans PLONE/ZINSTANCE
        with open('members.csv', 'w', newline='') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',')
            spamwriter.writerow(MEMBERFIELDS)

            members = api.user.get_users()
            for member in members:
                row = []

                for property in MEMBERFIELDS:
                    row.append(member.getProperty(property))

                spamwriter.writerow(row)

        # Redirect back to the listing view
        request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")


class MemberImportView(BrowserView):
    """Members import"""

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        request = self.context.REQUEST
        regtool = self.context.portal_registration

        csvfile_obj = self.context["membres.csv"]

        try:
            # Case of a Plone / DX File
            # print(dir(csvfile_obj.file))
            csvcontent = csvfile_obj.file
            # print(csvcontent.data)

            data = csvcontent.data.decode("utf-8")

            rows = data.split("\r\n")
            fieldnames = rows[0].split(";")  # beware!

            for row in rows[1:]:
                rowdata = {}

                # print(row)
                values = row.split(";")
                for idx, name in enumerate(fieldnames):
                    try:
                        rowdata[name] = values[idx].strip()
                    except Exception:
                        pass

                # Transform rowdata into userdata
                userdata = {}
                for name in MEMBERFIELDS:
                    userdata[name] = rowdata[name]
                # also add the 'username' key to the data dict
                userdata["username"] = rowdata["email"]

                # prepare username / password
                username = userdata["username"]
                password = self._generateRandomPassword(8)

                # Now the core of the process
                try:
                    regtool.addMember(username, password, properties=userdata)

                    # PAS D'AJOUT DE GROUP pour l'instant
                    # if userdata.get('group') and self.can_manage_groups:
                    #     group=userdata.get('group')
                    #     api.group.add_user(groupname=group, username=username)

                    # Send confirmation with details to the user
                    if userdata.get('email', ""):
                        mailhost = self.context.MailHost
                        dest_email = userdata['email']
                        send_email = self.context.getProperty('email_from_address')
                        msg = f"Confirmation de compte créé : {userdata}. Mot de passe à changer au plus vite : {password}"
                        subject = "Votre compte a été créé"

                        try:
                            mailhost.send(msg, dest_email, send_email, subject)
                            logger.info("Message emailed.")
                        except Exception:
                            logger.error(f"SMTP exception while trying to send an email to {dest_email}")

                except Exception as e:
                    logger.error(str(e))
        except Exception as e:
            print(str(e))

        # import pdb; pdb.set_trace()

        # Redirect back to the listing view
        self.request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")

    @property
    def all_groups(self):
        acl_users = self.context.acl_users
        return acl_users.source_groups.getGroupIds()

    def can_manage_groups(self):
        mtool = self.context.portal_membership
        return mtool.checkPermission(ManageGroups, self.context)

    def _addUserToGroups(self, username, groups):
        acl_users = self.context.acl_users
        for group_id in groups:
            group = acl_users.getGroup(group_id)
            group.addMember(username)

    def _generateRandomPassword(self, chars):
        st = ""
        possible_chars = 'qwertyuiopasdfghjklzxcvbnm_-1234567890'
        for x in range(chars):
            st+=random.choice(possible_chars)
        return st


class MemberDeleteView(BrowserView):
    """Members delete"""

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        request = self.context.REQUEST
        mtool = self.context.portal_membership
        members = api.user.get_users()

        DO_NOT_DELETE = ("kamona", )

        for m in members:
            m_id = m.member_id
            if m_id not in DO_NOT_DELETE:
                print(f"Preparing to delete {m_id}")
                mtool.deleteMembers((m_id,))
                print(f"Deleted {m_id}")

        # Redirect back to the listing view
        self.request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")


class MemberFormView(BrowserView):
    """Members updating form"""

    def __call__(self):
        exclude_memberIds = ["portal_skin","listed","login_time","last_login_time","error_log_update","language","ext_editor","wysiwyg_editor","visible_ids","home_page","location"]
        memberIds = []

        request = self.context.REQUEST
        form_data = request.form

        members = api.user.get_users()
        ids = self.context.portal_memberdata.propertyIds()

        for id in ids:
            if id not in exclude_memberIds:
                memberIds.append(id)

        for member in members:
            for id in memberIds:
                input_name = str(member) + '_' + str(id)

                if type(member.getProperty(id)) is bool and member.getProperty(id)==False and input_name in form_data.keys():
                    member.setMemberProperties(mapping={id:True})

                elif type(member.getProperty(id)) is bool and member.getProperty(id)==True and input_name not in form_data.keys():
                    member.setMemberProperties(mapping={id:False})

        # Redirect back to the listing view
        request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")
