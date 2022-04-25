# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from plone import api
from plone.app.testing import setRoles, TEST_USER_ID
from sesamath.customization.testing import (
    SESAMATH_CUSTOMIZATION_INTEGRATION_TESTING,  # noqa: E501,
)

import unittest


try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


class TestSetup(unittest.TestCase):
    """Test that sesamath.customization is properly installed."""

    layer = SESAMATH_CUSTOMIZATION_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")

    def test_product_installed(self):
        """Test if sesamath.customization is installed."""
        self.assertTrue(self.installer.isProductInstalled("sesamath.customization"))

    def test_browserlayer(self):
        """Test that ISesamathCustomizationLayer is registered."""
        from sesamath.customization.interfaces import ISesamathCustomizationLayer
        from plone.browserlayer import utils

        self.assertIn(ISesamathCustomizationLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = SESAMATH_CUSTOMIZATION_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstallProducts(["sesamath.customization"])
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if sesamath.customization is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled("sesamath.customization"))

    def test_browserlayer_removed(self):
        """Test that ISesamathCustomizationLayer is removed."""
        from sesamath.customization.interfaces import ISesamathCustomizationLayer
        from plone.browserlayer import utils

        self.assertNotIn(ISesamathCustomizationLayer, utils.registered_layers())
