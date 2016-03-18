import logging
import os
from unittest import TestCase

from piplapis.data import Person, Email, Name, URL, Username, UserID, Image, Phone, Address, OriginCountry, Language, \
    DOB, Gender, Job, Education
from piplapis.data.containers import Relationship
from piplapis.search import SearchAPIRequest

# Tests for the pipl API using the python client library
# These tests expect two environment variables to be set:
# TESTING_KEY: the API key to use
# API_TESTS_BASE_URL: the base URL on which to execute requests

handler = logging.StreamHandler()
logging.getLogger('piplapis').addHandler(handler)


class APITests(TestCase):

    def setUp(self):
        SearchAPIRequest.default_api_key = os.getenv("TESTING_KEY")
        SearchAPIRequest.BASE_URL = os.getenv("API_TESTS_BASE_URL") + "?developer_class=business_premium"

    def get_broad_search_request(self):
        return SearchAPIRequest(first_name="brian", last_name="perks")

    def get_narrow_search_request(self):
        return SearchAPIRequest(email="brianperks@gmail.com")

    def get_narrow_md5_search_request(self):
        return SearchAPIRequest(person=Person(fields=[
            Email(address_md5="e34996fda036d60aa2a595ca86ed8fef")]))

    def test_basic_request(self):
        response = self.get_broad_search_request().send()
        self.assertEquals(response.http_status_code, 200)

    def test_search_makes_a_match_request(self):
        response = self.get_narrow_search_request().send()
        self.assertEquals(response.http_status_code, 200)
        self.assertIsNotNone(response.person)

    def test_recursive_request(self):
        response = self.get_broad_search_request().send()
        self.assertGreater(len(response.possible_persons), 0)
        second_response = SearchAPIRequest(search_pointer=response.possible_persons[0].search_pointer).send()
        self.assertIsNotNone(second_response.person)

    def test_make_sure_hide_sponsored_works(self):
        request = self.get_narrow_search_request()
        request.hide_sponsored = True
        response = request.send()
        sponsored_links = [x for x in response.person.urls if x.sponsored]
        self.assertEquals(len(sponsored_links), 0)

    def test_make_sure_we_can_hide_inferred(self):
        request = self.get_narrow_search_request()
        request.minimum_probability = 1.
        response = request.send()
        inferred_data = [x for x in response.person.all_fields if x.inferred]
        self.assertEquals(len(inferred_data), 0)

    def test_make_sure_we_get_inferred(self):
        request = self.get_narrow_search_request()
        request.minimum_probability = .5
        response = request.send()
        inferred_data = [x for x in response.person.all_fields if x.inferred]
        self.assertGreater(len(inferred_data), 0)

    def test_make_sure_show_sources_matching_works(self):
        request = self.get_narrow_search_request()
        request.show_sources = "matching"
        response = request.send()
        self.assertGreater(len(response.sources), 0)
        non_matching_sources = [x for x in response.sources if x.person_id != response.person.person_id]
        self.assertEquals(len(non_matching_sources), 0)

    def test_make_sure_show_sources_all_works(self):
        request = self.get_narrow_search_request()
        request.show_sources = "all"
        response = request.send()
        non_matching_sources = [x for x in response.sources if x.person_id != response.person.person_id]
        self.assertGreater(len(non_matching_sources), 0)

    def test_make_sure_minimum_match_works(self):
        request = self.get_broad_search_request()
        request.minimum_match = 0.7
        response = request.send()
        persons_below_match = [x for x in response.possible_persons if x.match < 0.7]
        self.assertEquals(len(persons_below_match), 0)

    def test_make_sure_deserialization_works(self):
        response = SearchAPIRequest(email="clark.kent@example.com").send()
        self.assertEquals(response.person.names[0].display, "Clark Joseph Kent")
        self.assertEquals(response.person.emails[1].address_md5, "999e509752141a0ee42ff455529c10fc")
        self.assertEquals(response.person.usernames[0].content, "superman@facebook")
        self.assertEquals(response.person.addresses[1].display, "1000-355 Broadway, Metropolis, Kansas")
        self.assertEquals(response.person.jobs[0].display, "Field Reporter at The Daily Planet (2000-2012)")
        self.assertEquals(response.person.educations[0].degree, "B.Sc Advanced Science")

    def test_make_sure_md5_search_works(self):
        self.assertIsNotNone(self.get_narrow_md5_search_request().send().person)

    def test_contact_datatypes_are_as_expected(self):
        SearchAPIRequest.BASE_URL = os.getenv("API_TESTS_BASE_URL") + "?developer_class=contact"
        response = self.get_narrow_search_request().send()
        available_data_types = {Name, Gender, DOB, Language, OriginCountry, Address, Phone, Email, Job, Education,
                                Image, Language, Username, UserID, URL, Relationship}
        for field in response.person.all_fields:
            if type(field) == Email:
                self.assertEqual(field.address, 'full.email.available@professional.or.premium.subscription')
            else:
                self.assertIn(type(field), available_data_types)

    def test_social_datatypes_are_as_expected(self):
        SearchAPIRequest.BASE_URL = os.getenv("API_TESTS_BASE_URL") + "?developer_class=social"
        response = self.get_narrow_search_request().send()
        available_data_types = {Name, Gender, DOB, Language, OriginCountry, Address, Phone, Username, UserID, Image,
                                Relationship, URL, Education, Job, Email}
        for field in response.person.all_fields:
            if type(field) == Email:
                self.assertEqual(field.address, 'full.email.available@professional.or.premium.subscription')
            else:
                self.assertIn(type(field), available_data_types)

    def test_forward_compatibility(self):
        SearchAPIRequest.BASE_URL += "&show_unknown_fields=1"
        request = SearchAPIRequest(email="clark.kent@example.com")
        response = request.send()
        self.assertIsNotNone(response.person)

    def test_make_sure_insufficient_search_isnt_sent(self):
        request = SearchAPIRequest(first_name="brian")
        try:
            request.send()
            failed = False
        except Exception as e:
            failed = True
        self.assertTrue(failed)
