# -*- coding: utf-8 -*-

from Products.Five.browser import BrowserView
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides
from Products.PlonePAS.permissions import ManageGroups
from plone import api

from plone.namedfile.file import NamedBlobFile

import csv
from datetime import datetime
import transaction
# from io import StringIO
import logging
import random

logger = logging.getLogger(__name__)


MEMBERFIELDS = [
    # "user_id",
    "email",
    "fullname",
    "description",
    "location",
    "cotisation_2021",
    "cotisation_2022",
    # "test", "fonction",
]


class MemberListView(BrowserView):
    """Members listing"""

    def table_columns(self):
        exclude_memberIds = [
            "portal_skin",
            "listed",
            "login_time",
            "last_login_time",
            "error_log_update",
            "language",
            "ext_editor",
            "wysiwyg_editor",
            "visible_ids",
            "home_page",
            "location",
        ]
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
        alsoProvides(self.request, IDisableCSRFProtection)

        logger.info("Start exporting members")

        # Cette partie du code génère le fichier MEMBERS.CSV sous PLONE/ZINSTANCE
        with open("members.csv", "w", newline="") as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=",")
            spamwriter.writerow(MEMBERFIELDS)

            members = api.user.get_users()
            for member in members:
                row = []
                for property in MEMBERFIELDS:
                    try:
                        val = member.getProperty(property)
                    except Exception:
                        val = ""
                    row.append(val)
                spamwriter.writerow(row)

        # => Objet "DX File" à la racine du site Plone
        logger.info("Create the members file within the Plone site")
        with open("members.csv", "r") as f:
            data = f.read()
            file_field = NamedBlobFile(data, filename="members-exported.csv")

            now = datetime.now()
            obj_id = f"members-export-{now.strftime('%Y%m%d-%H%M')}.csv"
            obj_title = f"Members export - {now.strftime('%Y%m%d %H:%M')}"

            try:
                self.context.invokeFactory(
                    "File",
                    obj_id,
                    title=obj_title,
                    description="Members data export",
                )
                new = self.context[obj_id]
                # set the file field on the content object
                new.file = file_field
                transaction.savepoint(1)
                logger.info(new.Title().upper())

                # => Remove the members.csv file from the file system

            except Exception as e:
                logger.info(f"Error: {e}")

        # Redirect back to the listing view
        self.request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")


class MemberImportView(BrowserView):
    """Members import"""

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        regtool = self.context.portal_registration
        try:
            csvfile_obj = self.context["membres.csv"]
        except Exception:
            csvfile_obj = self.context["members.csv"]

        # try:
        # Case of a Plone / DX File
        csvcontent = csvfile_obj.file

        data = csvcontent.data.decode("utf-8")
        # logger.info(data)

        if "\r\n" in data:
            rows = data.split("\r\n")
        elif "\n" in data:
            rows = data.split("\n")

        # which separator?
        sep = ","
        if ";" in rows[0]:
            sep = ";"

        # Get the fieldnames from the members file
        fieldnames = rows[0].split(sep)

        # logger.info(rows)

        for row in rows[1:]:
            logger.info(row)

            rowdata = {}

            # if sep in row:
            values = row.split(sep)
            logger.info(values)

            for idx, name in enumerate(fieldnames):
                try:
                    rowdata[name] = values[idx].strip()
                except Exception as e:
                    logger.info(str(e))

            # 'email' is the key field of the userdata, so we only proceed if it exists
            if "email" in rowdata:
                # also add the 'username' key to the data dict
                rowdata["username"] = rowdata["email"]

                # prepare username / password
                username = rowdata["username"]
                password = self._generateRandomPassword(8)

                # prepare groups
                groups_info = rowdata.get("groups", "")
                if groups_info:
                    groups = groups_info.split(",")
                else:
                    groups = []

                # Remove the 'groups' key from the row dict now, before next part
                try:
                    del rowdata["groups"]
                except Exception:
                    pass

                # Now the core of the process
                try:
                    # Add member
                    regtool.addMember(username, password, properties=rowdata)

                    # Add the member to groups
                    if groups and self.can_manage_groups:
                        for groupname in groups:
                            api.group.add_user(groupname=groupname, username=username)

                    # Send confirmation with details to the user
                    mailhost = self.context.MailHost
                    dest_email = rowdata["email"]
                    send_email = self.context.getProperty("email_from_address")
                    msg = f"Votre compte a été créé : {username}. Mot de passe par défaut : {password}. Veuiller le changer au plus vite."
                    subject = "Votre compte a été créé"

                    try:
                        mailhost.send(msg, dest_email, send_email, subject)
                        logger.info("Message emailed.")
                    except Exception:
                        logger.error(
                            f"SMTP exception while trying to send an email to {dest_email}"
                        )

                except Exception as e:
                    logger.error(str(e))
            # except Exception as e:
            #     print(str(e))

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
        possible_chars = "qwertyuiopasdfghjklzxcvbnm_-1234567890"
        for x in range(chars):
            st += random.choice(possible_chars)
        return st


class MemberDeleteView(BrowserView):
    """Members delete"""

    def __call__(self):
        alsoProvides(self.request, IDisableCSRFProtection)

        mtool = self.context.portal_membership
        members = api.user.get_users()

        DO_NOT_DELETE = ["kamona",]
        try:
            members_not_delete = list(self.context.members_not_delete)
        except Exception:
            members_not_delete = []
        members_not_delete = list(set(members_not_delete + DO_NOT_DELETE))
        logger.info(members_not_delete)

        for m in members:
            # logger.info(m)
            # logger.info(str(m))
            m_id = m.getProperty("id")
            if m_id not in members_not_delete:
                logger.info(f"Preparing to delete {m_id}")
                mtool.deleteMembers((m_id,))
                logger.info(f"Deleted {m_id}")

        # Redirect back to the listing view
        self.request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")


class MemberFormView(BrowserView):
    """Members updating form"""

    def __call__(self):
        exclude_memberIds = [
            "portal_skin",
            "listed",
            "login_time",
            "last_login_time",
            "error_log_update",
            "language",
            "ext_editor",
            "wysiwyg_editor",
            "visible_ids",
            "home_page",
            "location",
        ]
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
                input_name = str(member) + "_" + str(id)

                if (
                    type(member.getProperty(id)) is bool
                    and member.getProperty(id) == False
                    and input_name in form_data.keys()
                ):
                    member.setMemberProperties(mapping={id: True})

                elif (
                    type(member.getProperty(id)) is bool
                    and member.getProperty(id) == True
                    and input_name not in form_data.keys()
                ):
                    member.setMemberProperties(mapping={id: False})

        # Redirect back to the listing view
        request.RESPONSE.redirect(self.context.absolute_url() + "/memberlist")
