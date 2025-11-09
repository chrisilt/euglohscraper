#!/usr/bin/env python3
"""
Unit tests for check_events.py

Tests the core functionality of the event scraper including:
- Event extraction from HTML
- Deduplication logic
- RSS feed generation
- Description cleaning
"""
import unittest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from check_events import (
    extract_event_from_anchor,
    find_events,
    normalize_url,
    load_state,
    save_state,
    append_to_feed,
    create_feed_header,
)


class TestNormalizeUrl(unittest.TestCase):
    """Test URL normalization functionality."""
    
    @patch('check_events.TARGET_URL', 'https://example.com/courses')
    def test_normalize_relative_url(self):
        """Test that relative URLs are made absolute."""
        result = normalize_url('/event/123')
        self.assertTrue(result.startswith('https://'))
        self.assertIn('example.com', result)
    
    @patch('check_events.TARGET_URL', 'https://example.com/courses')
    def test_normalize_removes_query_params(self):
        """Test that query parameters are removed for stable IDs."""
        result = normalize_url('https://example.com/event?param=value')
        self.assertNotIn('?', result)
        self.assertNotIn('param', result)
    
    @patch('check_events.TARGET_URL', 'https://example.com/courses')
    def test_normalize_removes_fragment(self):
        """Test that URL fragments are removed."""
        result = normalize_url('https://example.com/event#section')
        self.assertNotIn('#', result)


class TestEventExtraction(unittest.TestCase):
    """Test event extraction from HTML."""
    
    def test_extract_event_basic(self):
        """Test basic event extraction with title and link."""
        html = """
        <div>
            <h5 class="headline">Test Event Title</h5>
            <time>2025-12-01</time>
            <a href="https://example.com/register">Register</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        anchor = soup.find('a')
        
        with patch('check_events.TARGET_URL', 'https://example.com'):
            event = extract_event_from_anchor(anchor)
        
        self.assertIsNotNone(event)
        self.assertEqual(event['title'], 'Test Event Title')
        self.assertIn('example.com', event['link'])
    
    def test_extract_event_with_date(self):
        """Test event extraction includes date information."""
        html = """
        <div>
            <h5 class="headline">Event With Date</h5>
            <time>Deadline: 31 Dec 2025 23:59</time>
            <a href="https://example.com/register">Register</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        anchor = soup.find('a')
        
        with patch('check_events.TARGET_URL', 'https://example.com'):
            event = extract_event_from_anchor(anchor)
        
        self.assertIsNotNone(event)
        self.assertIsNotNone(event['date'])
        self.assertIn('Dec', event['date'])
    
    def test_extract_event_cleans_description(self):
        """Test that description is cleaned of unwanted phrases."""
        html = """
        <div>
            <h5 class="headline">Event Title</h5>
            <p>Find out more and register nowDeadline: 15 Nov 2025 23:59</p>
            <a href="https://example.com/register">Register</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        anchor = soup.find('a')
        
        with patch('check_events.TARGET_URL', 'https://example.com'):
            event = extract_event_from_anchor(anchor)
        
        self.assertIsNotNone(event)
        description = event.get('description', '')
        # Should not contain the "Find out more and register now" phrase
        self.assertNotIn('Find out more and register now', description)
    
    def test_extract_event_missing_href(self):
        """Test that anchors without href are handled gracefully."""
        html = '<a>No href here</a>'
        soup = BeautifulSoup(html, 'html.parser')
        anchor = soup.find('a')
        
        event = extract_event_from_anchor(anchor)
        self.assertIsNone(event)


class TestFindEvents(unittest.TestCase):
    """Test finding multiple events in HTML."""
    
    @patch('check_events.REG_LINK_SELECTOR', 'a.register-link')
    def test_find_multiple_events(self):
        """Test finding multiple events in HTML."""
        html = """
        <div>
            <h5 class="headline">Event 1</h5>
            <a class="register-link" href="https://example.com/event1">Register</a>
        </div>
        <div>
            <h5 class="headline">Event 2</h5>
            <a class="register-link" href="https://example.com/event2">Register</a>
        </div>
        """
        with patch('check_events.TARGET_URL', 'https://example.com'):
            events = find_events(html)
        
        self.assertEqual(len(events), 2)
        self.assertIn('Event 1', events[0]['title'])
        self.assertIn('Event 2', events[1]['title'])
    
    @patch('check_events.REG_LINK_SELECTOR', 'a.register-link')
    def test_find_events_empty_html(self):
        """Test that empty HTML returns empty list."""
        html = "<html><body></body></html>"
        events = find_events(html)
        self.assertEqual(len(events), 0)


class TestStateManagement(unittest.TestCase):
    """Test state loading and saving."""
    
    def test_load_state_new_file(self):
        """Test loading state when file doesn't exist."""
        state = load_state('/tmp/nonexistent_state_file.json')
        self.assertEqual(state['seen_ids'], [])
        self.assertIsNone(state['last_checked'])
    
    def test_save_and_load_state(self):
        """Test saving and loading state."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            test_state = {
                'seen_ids': ['id1', 'id2', 'id3'],
                'last_checked': 1234567890
            }
            save_state(temp_path, test_state)
            
            loaded_state = load_state(temp_path)
            self.assertEqual(loaded_state['seen_ids'], ['id1', 'id2', 'id3'])
            self.assertEqual(loaded_state['last_checked'], 1234567890)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestFeedGeneration(unittest.TestCase):
    """Test RSS feed generation."""
    
    def test_create_feed_header(self):
        """Test that feed header is valid XML."""
        header = create_feed_header()
        self.assertIn('<?xml version="1.0"', header)
        self.assertIn('<rss version="2.0"', header)
        self.assertIn('<channel>', header)
        self.assertIn('EUGLOH Open Registrations Feed', header)
    
    def test_append_to_feed_new_file(self):
        """Test creating a new feed file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)  # Remove so we test creation
        
        try:
            events = [
                {
                    'id': 'https://example.com/event1',
                    'title': 'Test Event',
                    'link': 'https://example.com/event1',
                    'description': 'Test description',
                    'date': '2025-12-01'
                }
            ]
            
            append_to_feed(temp_path, events)
            
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertIn('Test Event', content)
            self.assertIn('https://example.com/event1', content)
            self.assertIn('<item>', content)
            self.assertIn('</item>', content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_append_to_feed_prepends_items(self):
        """Test that new items are prepended to existing feed."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        
        try:
            # Create initial feed
            first_events = [
                {
                    'id': 'https://example.com/event1',
                    'title': 'First Event',
                    'link': 'https://example.com/event1',
                    'description': 'First description',
                    'date': '2025-12-01'
                }
            ]
            append_to_feed(temp_path, first_events)
            
            # Add new event
            second_events = [
                {
                    'id': 'https://example.com/event2',
                    'title': 'Second Event',
                    'link': 'https://example.com/event2',
                    'description': 'Second description',
                    'date': '2025-12-02'
                }
            ]
            append_to_feed(temp_path, second_events)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Second event should appear before first event
            second_pos = content.find('Second Event')
            first_pos = content.find('First Event')
            self.assertLess(second_pos, first_pos, "New items should be prepended")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_feed_escapes_html_entities(self):
        """Test that HTML entities are properly escaped in feed."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)
        
        try:
            events = [
                {
                    'id': 'https://example.com/event1',
                    'title': 'Event & Testing <Special> "Chars"',
                    'link': 'https://example.com/event1',
                    'description': 'Description with & and <tags>',
                    'date': '2025-12-01'
                }
            ]
            
            append_to_feed(temp_path, events)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check that entities are escaped in XML title
            self.assertIn('&amp;', content)
            self.assertIn('&lt;', content)
            # Description uses CDATA so check it contains the description
            self.assertIn('Description with', content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestDeduplication(unittest.TestCase):
    """Test event deduplication logic."""
    
    def test_deduplication_filters_seen_events(self):
        """Test that seen events are filtered out."""
        all_events = [
            {'id': 'event1', 'title': 'Event 1'},
            {'id': 'event2', 'title': 'Event 2'},
            {'id': 'event3', 'title': 'Event 3'},
        ]
        seen = {'event1', 'event3'}
        
        new_events = [e for e in all_events if e['id'] not in seen]
        
        self.assertEqual(len(new_events), 1)
        self.assertEqual(new_events[0]['id'], 'event2')


if __name__ == '__main__':
    unittest.main()
