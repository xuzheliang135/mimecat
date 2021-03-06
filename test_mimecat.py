# -*- coding: utf-8 -*-
import os
import unittest
from StringIO import StringIO

from mimecat import (Catalogue, _canonicalize_extension,
                     _parse_file, _parse_line)

TEST_MIME_TYPES = """
# This file maps Internet media types to unique file extension(s).
# Although created for httpd, this file is used by many software systems
# and has been placed in the public domain for unlimited redisribution.
#
# The table below contains both registered and (common) unregistered types.
# A type that has no unique extension can be ignored -- they are listed
# here to guide configurations toward known types and to make it easier to
# identify "new" types.  File extensions are also commonly used to indicate
# content languages and encodings, so choose them carefully.
#
# Internet media types should be registered as described in RFC 4288.
# The registry is at <http://www.iana.org/assignments/media-types/>.
#
# MIME type (lowercased)			Extensions
# ============================================	==========
# application/activemessage
application/andrew-inset			ez
application/json				json
# application/kpml-request+xml
# audio/amr
audio/midi					mid midi kar rmi
# audio/mobile-xmf
audio/mp4					mp4a
audio/mp4a-latm			m4a m4p
audio/ogg					oga ogg spx
image/jpeg					jpeg jpg jpe
# image/jpm
# message/cpim
# message/delivery-status
message/rfc822					eml mime
text/css					css
text/plain					txt text conf def list log in
# text/xml
video/3gpp					3gp
video/3gpp2					3g2
video/ogg					ogv
"""

class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_filename = "test.mime.types"
        cls.test_filename_shibboleth = "test-shibboleth.mime.types"
        with open(cls.test_filename, "w") as filep:
            filep.write(TEST_MIME_TYPES)

        with open(cls.test_filename_shibboleth, "w") as filep:
            filep.write("text/plain2            txt\n")
            filep.write("text/plain            txt2\n")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.test_filename)
        os.unlink(cls.test_filename_shibboleth)

    def setUp(self):
        self.catalogue = Catalogue(self.test_filename)

        self.empty_catalogue = Catalogue(self.test_filename)
        self.empty_catalogue.clear()

    def test_init(self):
        cat = Catalogue(self.test_filename)
        self.assertIn("message/rfc822",
                      cat._known_mimetypes)

    def test_init_with_filep(self):
        with open(self.test_filename, "r") as filep:
            cat = Catalogue(filep = filep)
        self.assertIn("message/rfc822",
                      cat._known_mimetypes)

    def test_init_with_order(self):
        with open(self.test_filename, "r") as filep:
            cat = Catalogue(self.test_filename_shibboleth, filep)

        # test_filename should've been used first, so text/plain2 should
        # come after text/plain in the extensions to type map
        type_list = cat._exts_to_types[".txt"]
        self.assertGreater(type_list.index("text/plain2"),
                           type_list.index("text/plain"))


    def test_init_fails(self):
        cat = None
        with self.assertRaises(IOError):
            cat = Catalogue(["BOGUS_FILE"])
        self.assertIsNone(cat)

    def test_clear(self):
        self.catalogue.clear()
        self.assertEqual( {}, self.catalogue._types_to_exts)
        self.assertEqual( {}, self.catalogue._exts_to_types)
        self.assertEqual(set(), self.catalogue._known_mediatypes)
        self.assertEqual(set(), self.catalogue._known_mimetypes)
        self.assertEqual(set(), self.catalogue._known_extensions)

    def test_load_filenames_stops(self):
        self.empty_catalogue.load_filenames([self.test_filename_shibboleth,
                                             self.test_filename],
                                            True)

        self.assertEqual(len(self.empty_catalogue._known_mediatypes), 1)
        self.assertEqual(len(self.empty_catalogue._known_mimetypes), 2)
        self.assertEqual(len(self.empty_catalogue._known_extensions), 2)

    def test_load_filenames_does_not_stop(self):
        self.empty_catalogue.load_filenames([self.test_filename_shibboleth,
                                             self.test_filename], False)

        self.assertGreater(len(self.empty_catalogue._known_mediatypes), 1)
        self.assertGreater(len(self.empty_catalogue._known_mimetypes), 2)
        self.assertGreater(len(self.empty_catalogue._known_extensions), 2)

    def test_load_filenames_fail(self):
        with self.assertRaises(IOError):
            self.empty_catalogue.load_filenames(["BOGUS_FILE", "BOGUS_FILE2"])

    def test_load_filename(self):
        self.empty_catalogue.load_filename(self.test_filename_shibboleth)
        self.assertEqual(len(self.empty_catalogue._known_mediatypes), 1)
        self.assertEqual(len(self.empty_catalogue._known_mimetypes), 2)
        self.assertEqual(len(self.empty_catalogue._known_extensions), 2)

    def test_load_filename_fails(self):
        with self.assertRaises(IOError):
            self.empty_catalogue.load_filename("BOGUS_FILE")

    def test_load_file(self):
        with open(self.test_filename_shibboleth) as filep:
            self.empty_catalogue.load_file(filep)

        self.assertEqual(len(self.empty_catalogue._known_mediatypes), 1)
        self.assertEqual(len(self.empty_catalogue._known_mimetypes), 2)
        self.assertEqual(len(self.empty_catalogue._known_extensions), 2)

    def test_parse_file(self):
        with open(self.test_filename_shibboleth) as filep:
            items = [item for item in _parse_file(filep) if item is not None]
        self.assertEqual(len(items), 2)

        with open(self.test_filename) as filep:
            items = [item for item in _parse_file(filep) if item is not None]
        self.assertEqual(len(items), 13)

    def test_parse_line(self):
        result = _parse_line("#")
        self.assertIsNone(result)

        result = _parse_line("# more")
        self.assertIsNone(result)

        result = _parse_line("text/plain")
        self.assertEqual(("text/plain", []), result)

        result = _parse_line("text/plain ext1 ext2 ext3")
        self.assertEqual(("text/plain", [".ext1", ".ext2", ".ext3"]), result)

        result = _parse_line("text/plain ext1 ext2 ext3 # with comment")
        self.assertEqual(("text/plain", [".ext1", ".ext2", ".ext3"]), result)

        result = _parse_line("# text/plain ext1 ext2 ext3")
        self.assertIsNone(result)

        result = _parse_line("# text/plain ext1 ext2 ext3 # with comment")
        self.assertIsNone(result)

    def test_parse_line_fails(self):
        with self.assertRaises(ValueError):
            _ = _parse_line("invalid exts")

    def test_known_mediatypes(self):
        self.assertIn("application", self.catalogue.known_mediatypes)
        self.assertIn("text", self.catalogue.known_mediatypes)

    def test_known_mimetypes(self):
        self.assertIn("application/json", self.catalogue.known_mimetypes)
        self.assertIn("audio/mp4", self.catalogue.known_mimetypes)

    def test_known_extensions(self):
        self.assertIn(".ez", self.catalogue.known_extensions)
        self.assertIn(".m4a", self.catalogue.known_extensions)

    def test_get_extensions(self):
        exts = self.catalogue.get_extensions("audio/midi")
        self.assertEqual(len(exts), 4)

    def test_get_extensions_fails(self):
        with self.assertRaises(KeyError):
            self.catalogue.get_extensions("bad/type")

    def test_get_types(self):
        types = self.catalogue.get_types(".txt")
        self.assertEqual(len(types), 1)

        types = self.catalogue.get_types("txt")
        self.assertEqual(len(types), 1)

    def test_get_types_with_duplicate(self):
        self.catalogue.add_type("text/plain2", ".txt")
        types = self.catalogue.get_types("txt")
        self.assertIn("text/plain", types)
        self.assertIn("text/plain2", types)

    def test_get_types_fails(self):
        with self.assertRaises(KeyError):
            self.catalogue.get_types("asdf")

    def test_add_type(self):
        self.empty_catalogue.add_type("text/plain", "txt")
        self.assertIn("text", self.empty_catalogue._known_mediatypes)
        self.assertIn("text/plain", self.empty_catalogue._known_mimetypes)
        self.assertIn(".txt", self.empty_catalogue._known_extensions)

        self.empty_catalogue.clear()
        self.empty_catalogue.add_type("text/plain", ".txt")
        self.assertIn("text", self.empty_catalogue._known_mediatypes)
        self.assertIn("text/plain", self.empty_catalogue._known_mimetypes)
        self.assertIn(".txt", self.empty_catalogue._known_extensions)

        self.empty_catalogue.clear()
        self.empty_catalogue.add_type("text/plain", [".txt"])
        self.assertIn("text", self.empty_catalogue._known_mediatypes)
        self.assertIn("text/plain", self.empty_catalogue._known_mimetypes)
        self.assertIn(".txt", self.empty_catalogue._known_extensions)

    def test_add_types_with_duplicate_extensions(self):
        self.empty_catalogue.add_type("text/plain", "txt")
        self.empty_catalogue.add_type("text/doc", "txt")
        self.assertIn("text/plain", self.empty_catalogue._exts_to_types[".txt"])
        self.assertIn("text/doc", self.empty_catalogue._exts_to_types[".txt"])

        self.assertIn(".txt", self.empty_catalogue._types_to_exts["text/plain"])
        self.assertIn(".txt", self.empty_catalogue._types_to_exts["text/doc"])

    def test_add_type_fails(self):
        with self.assertRaises(ValueError):
            self.empty_catalogue.add_type("textplain", ".txt")

    def test_canonicalize_extension(self):
        ret = _canonicalize_extension("test")
        self.assertEqual(ret, ".test")

        ret = _canonicalize_extension(".test")
        self.assertEqual(ret, ".test")

        ret = _canonicalize_extension("")
        self.assertEqual(ret, "")

        ret = _canonicalize_extension(None)
        self.assertIsNone(ret)
