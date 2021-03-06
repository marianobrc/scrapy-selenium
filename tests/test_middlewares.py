"""This module contains the test cases for the middlewares of the ``scrapy_selenium`` package"""

from unittest.mock import patch

from scrapy import Request
from scrapy.crawler import Crawler

from scrapy_selenium.http import SeleniumRequest
from scrapy_selenium.middlewares import SeleniumMiddleware

from .test_cases import BaseScrapySeleniumTestCase


class SeleniumMiddlewareTestCase(BaseScrapySeleniumTestCase):
    """Test case for the ``SeleniumMiddleware`` middleware"""

    @classmethod
    def setUpClass(cls):
        """Initialize the middleware"""

        super().setUpClass()

        crawler = Crawler(
            spidercls=cls.spider_klass,
            settings=cls.settings
        )

        cls.selenium_middleware = SeleniumMiddleware.from_crawler(crawler)

    @classmethod
    def tearDownClass(cls):
        """Close the selenium webdriver"""

        super().tearDownClass()

        cls.selenium_middleware.spider_closed()

    def test_spider_closed_should_close_the_driver(self):
        """Test that the ``spider_closed`` method should close the driver"""

        crawler = Crawler(
            spidercls=self.spider_klass,
            settings=self.settings
        )

        selenium_middleware = SeleniumMiddleware.from_crawler(crawler)

        mocked_quit = [patch.object(driver, 'quit') for driver in selenium_middleware.drivers]
        for q in mocked_quit:
            q.assert_called_once()

    def test_process_request_should_return_none_if_not_selenium_request(self):
        """Test that the ``process_request`` should return none if not selenium request"""

        scrapy_request = Request(url='http://not-an-url')

        self.assertIsNone(
            self.selenium_middleware.process_request(
                request=scrapy_request,
                spider=None
            )
        )

    def test_process_request_should_return_a_response_if_selenium_request(self):
        """Test that the ``process_request`` should return a response if selenium request"""

        selenium_request = SeleniumRequest(url='http://www.python.org')

        html_response = self.selenium_middleware.process_request(
            request=selenium_request,
            spider=None
        )

        # We have access to the driver on the response via the "meta"
        self.assertEqual(
            html_response.meta['driver'],
            self.selenium_middleware.driver
        )

        # We also have access to the "selector" attribute on the response
        self.assertEqual(
            html_response.selector.xpath('//title/text()').extract_first(),
            'Welcome to Python.org'
        )

    def test_process_request_should_return_a_screenshot_if_screenshot_option(self):
        """Test that the ``process_request`` should return a response with a screenshot"""

        selenium_request = SeleniumRequest(
            url='http://www.python.org',
            screenshot=True
        )

        html_response = self.selenium_middleware.process_request(
            request=selenium_request,
            spider=None
        )

        self.assertIsNotNone(html_response.meta['screenshot'])

    def test_process_request_should_execute_script_if_script_option(self):
        """Test that the ``process_request`` should execute the script and return a response"""

        selenium_request = SeleniumRequest(
            url='http://www.python.org',
            script='document.title = "scrapy_selenium";'
        )

        html_response = self.selenium_middleware.process_request(
            request=selenium_request,
            spider=None
        )

        self.assertEqual(
            html_response.selector.xpath('//title/text()').extract_first(),
            'scrapy_selenium'
        )

    def test_max_concurrent_driver(self):
        """Test that up to max_concurrent_driver should be alive. Evicted driver should be closed."""
        self.selenium_middleware.process_request(SeleniumRequest(
            url='http://www.python.org',
            meta={'proxy': 'http://1.1.1.1'}
        ))
        self.assertEqual(len(self.selenium_middleware.drivers), 1)
        driver1 = self.selenium_middleware.drivers['http://1.1.1.1']
        self.selenium_middleware.process_request(SeleniumRequest(
            url='http://www.python.org',
            meta={'proxy': 'http://1.1.1.2'}
        ))
        self.assertEqual(len(self.selenium_middleware.drivers), 2)
        self.selenium_middleware.process_request(SeleniumRequest(
            url='http://www.python.org',
            meta={'proxy': 'http://1.1.1.3'}
        ))
        # one of the driver is evicted
        self.assertEqual(len(self.selenium_middleware.drivers), 2)
        # when driver quites, the session id will be None
        self.assertEqual(driver1.session_id, None)

    def test_same_proxy_should_reuse_driver(self):
        self.selenium_middleware.process_request(SeleniumRequest(
            url='http://www.python.org',
            meta={'proxy': 'http://1.1.1.1'}
        ))
        self.assertEqual(len(self.selenium_middleware.drivers), 1)
        driver1 = self.selenium_middleware.drivers['http://1.1.1.1']
        self.selenium_middleware.process_request(SeleniumRequest(
            url='http://www.python.org',
            meta={'proxy': 'http://1.1.1.1'}
        ))
        self.assertEqual(len(self.selenium_middleware.drivers), 1)
        driver2 = self.selenium_middleware.drivers['http://1.1.1.1']
        self.assertEqual(driver1.session_id, driver2.session_id)
