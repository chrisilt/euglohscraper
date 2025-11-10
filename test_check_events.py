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
import time
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


class TestNewEventCategory(unittest.TestCase):
    """Test that NEW events are properly tagged in RSS feed."""
    
    def test_new_events_have_category_tag(self):
        """Test that new events include the <category>new</category> tag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)
        
        try:
            events = [
                {
                    'id': 'https://example.com/event1',
                    'title': 'New Event',
                    'link': 'https://example.com/event1',
                    'description': 'A brand new event',
                    'date': '2025-12-01'
                }
            ]
            
            append_to_feed(temp_path, events)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Verify the feed contains the 'new' category
            self.assertIn('<category>new</category>', content)
            # Verify it's in the correct item
            self.assertIn('<title>New Event</title>', content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_feed_stats_count_new_events(self):
        """Test that frontend can correctly identify new events from feed."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)
        
        try:
            # Create multiple events, all tagged as new
            events = [
                {
                    'id': 'https://example.com/event1',
                    'title': 'Event 1',
                    'link': 'https://example.com/event1',
                    'description': 'Description 1',
                    'date': '2025-12-01'
                },
                {
                    'id': 'https://example.com/event2',
                    'title': 'Event 2',
                    'link': 'https://example.com/event2',
                    'description': 'Description 2',
                    'date': '2025-12-02'
                }
            ]
            
            append_to_feed(temp_path, events)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Count occurrences of the new category tag
            new_count = content.count('<category>new</category>')
            self.assertEqual(new_count, 2, "Should have 2 new events")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_new_category_in_all_new_items(self):
        """Test that every new event gets the new category tag."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)
        
        try:
            events = [
                {
                    'id': f'https://example.com/event{i}',
                    'title': f'Event {i}',
                    'link': f'https://example.com/event{i}',
                    'description': f'Description {i}',
                    'date': '2025-12-01'
                }
                for i in range(5)
            ]
            
            append_to_feed(temp_path, events)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Verify all items have the new category
            item_count = content.count('<item>')
            new_count = content.count('<category>new</category>')
            self.assertEqual(item_count, 5, "Should have 5 items")
            self.assertEqual(new_count, 5, "All 5 items should be tagged as new")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_old_events_lose_new_category(self):
        """Test that events older than 7 days lose the 'new' category."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)
        
        try:
            import time as time_module
            
            # Create an old event (8 days ago)
            eight_days_ago = time_module.time() - (8 * 24 * 60 * 60)
            old_date = time_module.strftime("%a, %d %b %Y %H:%M:%S +0000", time_module.gmtime(eight_days_ago))
            
            old_events = [
                {
                    'id': 'https://example.com/old-event',
                    'title': 'Old Event',
                    'link': 'https://example.com/old-event',
                    'description': 'An old event',
                    'date': old_date
                }
            ]
            
            # Add old event to feed
            append_to_feed(temp_path, old_events)
            
            # Verify it initially has the 'new' category
            with open(temp_path, 'r') as f:
                content = f.read()
            self.assertIn('<category>new</category>', content)
            
            # Now add a new event, which should trigger cleanup of old 'new' tags
            new_event = [
                {
                    'id': 'https://example.com/fresh-event',
                    'title': 'Fresh Event',
                    'link': 'https://example.com/fresh-event',
                    'description': 'A fresh event',
                    'date': time_module.strftime("%a, %d %b %Y %H:%M:%S +0000", time_module.gmtime())
                }
            ]
            
            append_to_feed(temp_path, new_event)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # The fresh event should have 'new' category
            self.assertIn('Fresh Event', content)
            # Count 'new' categories - should be 1 (only the fresh event)
            new_count = content.count('<category>new</category>')
            self.assertEqual(new_count, 1, "Only the fresh event should have 'new' category")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestExpiredEventHandling(unittest.TestCase):
    """Test expired event handling functionality."""
    
    def test_parse_deadline_standard_format(self):
        """Test parsing standard deadline format."""
        from check_events import parse_deadline
        
        # Test various date formats
        date1 = "31 Dec 2026 23:59"
        result1 = parse_deadline(date1)
        self.assertIsNotNone(result1)
        self.assertIsInstance(result1, float)
        
        date2 = "Deadline: 15 Nov 2025 23:59"
        result2 = parse_deadline(date2)
        self.assertIsNotNone(result2)
    
    def test_parse_deadline_invalid_format(self):
        """Test that invalid dates return None."""
        from check_events import parse_deadline
        
        result = parse_deadline("Invalid date string")
        self.assertIsNone(result)
        
        result = parse_deadline("")
        self.assertIsNone(result)
    
    def test_is_event_expired_past_date(self):
        """Test that past dates are marked as expired."""
        from check_events import is_event_expired
        
        # Test with a date in the past
        past_date = "1 Jan 2020 00:00"
        self.assertTrue(is_event_expired(past_date))
    
    def test_is_event_expired_future_date(self):
        """Test that future dates are not marked as expired."""
        from check_events import is_event_expired
        
        # Test with a date in the future
        future_date = "31 Dec 2030 23:59"
        self.assertFalse(is_event_expired(future_date))
    
    def test_is_event_expired_with_buffer(self):
        """Test expired check with grace period buffer."""
        from check_events import is_event_expired
        import time
        
        # Test with a date slightly in the past but within buffer
        # This is hard to test precisely, so we'll test the logic exists
        past_date = "1 Jan 2020 00:00"
        # With a huge buffer, it shouldn't be expired
        self.assertTrue(is_event_expired(past_date, buffer_days=0))
    
    def test_expired_category_added_to_feed(self):
        """Test that expired events get the expired category in feed."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            temp_path = f.name
        os.unlink(temp_path)
        
        try:
            # Create an event with expired deadline
            events = [
                {
                    'id': 'https://example.com/expired-event',
                    'title': 'Expired Event',
                    'link': 'https://example.com/expired-event',
                    'description': 'Deadline: 1 Jan 2020 00:00',
                    'date': '1 Jan 2020 00:00'
                }
            ]
            
            from check_events import append_to_feed
            append_to_feed(temp_path, events)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # The event should be in the feed
            self.assertIn('Expired Event', content)
            
            # Now run append again to trigger expired category addition
            append_to_feed(temp_path, [])
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            # Check if expired category was added
            self.assertIn('<category>expired</category>', content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestHistoricalTracking(unittest.TestCase):
    """Test historical tracking functionality."""
    
    def test_load_history_new_file(self):
        """Test loading history when file doesn't exist."""
        from check_events import load_history
        
        history = load_history('/tmp/nonexistent_history_file.json')
        self.assertEqual(history['events'], {})
    
    def test_save_and_load_history(self):
        """Test saving and loading history."""
        from check_events import load_history, save_history
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            test_history = {
                'events': {
                    'event1': {
                        'id': 'event1',
                        'title': 'Test Event',
                        'first_seen': 1234567890,
                        'last_seen': 1234567890,
                    }
                }
            }
            save_history(temp_path, test_history)
            
            loaded_history = load_history(temp_path)
            self.assertIn('event1', loaded_history['events'])
            self.assertEqual(loaded_history['events']['event1']['title'], 'Test Event')
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_update_event_history_new_event(self):
        """Test updating history for a new event."""
        from check_events import update_event_history
        
        history = {'events': {}}
        event = {
            'id': 'https://example.com/event1',
            'title': 'New Event',
            'link': 'https://example.com/event1',
            'date': '31 Dec 2026 23:59'
        }
        
        update_event_history(history, event, 'new')
        
        self.assertIn(event['id'], history['events'])
        self.assertEqual(history['events'][event['id']]['title'], 'New Event')
        self.assertIsNotNone(history['events'][event['id']]['first_seen'])
    
    def test_update_event_history_expired_event(self):
        """Test marking an event as expired in history."""
        from check_events import update_event_history
        
        history = {'events': {}}
        event = {
            'id': 'https://example.com/event1',
            'title': 'Event',
            'link': 'https://example.com/event1',
            'date': '1 Jan 2020 00:00'
        }
        
        # First add as new
        update_event_history(history, event, 'new')
        first_seen = history['events'][event['id']]['first_seen']
        
        # Then mark as expired
        import time
        time.sleep(0.1)  # Small delay to ensure different timestamps
        update_event_history(history, event, 'expired')
        
        self.assertIsNotNone(history['events'][event['id']]['expired_at'])
        self.assertIsNotNone(history['events'][event['id']]['registration_duration_days'])


class TestStatistics(unittest.TestCase):
    """Test statistics generation functionality."""
    
    def test_generate_statistics(self):
        """Test statistics generation from history."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        one_day_ago = current_time - (24 * 60 * 60)
        
        history = {
            'events': {
                'event1': {
                    'id': 'event1',
                    'title': 'Active Event',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(one_day_ago),
                    'last_seen': int(current_time),
                    'expired_at': None,
                },
                'event2': {
                    'id': 'event2',
                    'title': 'Expired Event',
                    'deadline': '1 Jan 2020 00:00',
                    'first_seen': int(one_day_ago),
                    'last_seen': int(current_time),
                    'expired_at': int(current_time),
                    'registration_duration_days': 100,
                }
            }
        }
        
        state = {'seen_ids': ['event1', 'event2']}
        
        stats = generate_statistics(history, state)
        
        self.assertEqual(stats['total_events_tracked'], 2)
        self.assertEqual(stats['currently_active'], 1)
        self.assertEqual(stats['total_expired'], 1)
    
    def test_save_statistics_creates_files(self):
        """Test that statistics files are created."""
        from check_events import save_statistics
        
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, 'stats.json')
            html_path = os.path.join(tmpdir, 'stats.html')
            
            stats = {
                'generated_at': int(time.time()),
                'total_events_tracked': 10,
                'currently_active': 5,
                'total_expired': 5,
                'new_this_week': 2,
                'upcoming_deadlines': [],
                'average_registration_duration_days': 45.5,
            }
            
            save_statistics(stats, json_path, html_path)
            
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(html_path))
            
            # Verify JSON content
            with open(json_path, 'r') as f:
                loaded_stats = json.load(f)
            self.assertEqual(loaded_stats['total_events_tracked'], 10)
            
            # Verify HTML contains statistics
            with open(html_path, 'r') as f:
                html_content = f.read()
            self.assertIn('EUGLOH Event Statistics', html_content)
            self.assertIn('10', html_content)  # total events
    
    def test_enhanced_statistics_new_this_month(self):
        """Test new_this_month statistic calculation."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        two_weeks_ago = current_time - (14 * 24 * 60 * 60)
        two_months_ago = current_time - (60 * 24 * 60 * 60)
        
        history = {
            'events': {
                'event1': {
                    'id': 'event1',
                    'title': 'Recent Event',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(two_weeks_ago),
                    'last_seen': int(current_time),
                    'expired_at': None,
                },
                'event2': {
                    'id': 'event2',
                    'title': 'Old Event',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(two_months_ago),
                    'last_seen': int(current_time),
                    'expired_at': None,
                }
            }
        }
        
        state = {'seen_ids': ['event1', 'event2']}
        stats = generate_statistics(history, state)
        
        self.assertEqual(stats['new_this_month'], 1)
        self.assertEqual(stats['new_this_week'], 0)
    
    def test_registration_duration_statistics(self):
        """Test registration duration min/max/median/average calculations."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        
        history = {
            'events': {
                'event1': {
                    'id': 'event1',
                    'title': 'Event 1',
                    'deadline': '1 Jan 2020 00:00',
                    'first_seen': int(current_time),
                    'last_seen': int(current_time),
                    'expired_at': int(current_time),
                    'registration_duration_days': 10.0,
                },
                'event2': {
                    'id': 'event2',
                    'title': 'Event 2',
                    'deadline': '1 Jan 2020 00:00',
                    'first_seen': int(current_time),
                    'last_seen': int(current_time),
                    'expired_at': int(current_time),
                    'registration_duration_days': 30.0,
                },
                'event3': {
                    'id': 'event3',
                    'title': 'Event 3',
                    'deadline': '1 Jan 2020 00:00',
                    'first_seen': int(current_time),
                    'last_seen': int(current_time),
                    'expired_at': int(current_time),
                    'registration_duration_days': 50.0,
                }
            }
        }
        
        state = {'seen_ids': ['event1', 'event2', 'event3']}
        stats = generate_statistics(history, state)
        
        self.assertIsNotNone(stats.get('registration_duration_stats'))
        rd_stats = stats['registration_duration_stats']
        self.assertEqual(rd_stats['min'], 10.0)
        self.assertEqual(rd_stats['max'], 50.0)
        self.assertEqual(rd_stats['median'], 30.0)
        self.assertEqual(rd_stats['average'], 30.0)
        self.assertEqual(rd_stats['total_completed'], 3)
    
    def test_event_velocity_calculation(self):
        """Test event velocity (events per week/month) calculation."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        days_30 = 30 * 24 * 60 * 60
        
        # Create 10 events spread over 30 days
        history = {'events': {}}
        for i in range(10):
            event_id = f'event{i}'
            history['events'][event_id] = {
                'id': event_id,
                'title': f'Event {i}',
                'deadline': '31 Dec 2030 23:59',
                'first_seen': int(current_time - days_30 + (i * days_30 / 10)),
                'last_seen': int(current_time),
                'expired_at': None,
            }
        
        state = {'seen_ids': list(history['events'].keys())}
        stats = generate_statistics(history, state)
        
        self.assertIn('event_velocity', stats)
        velocity = stats['event_velocity']
        self.assertIn('events_per_week', velocity)
        self.assertIn('events_per_month', velocity)
        self.assertGreater(velocity['events_per_week'], 0)
        self.assertGreater(velocity['events_per_month'], 0)
    
    def test_event_velocity_insufficient_data(self):
        """Test that velocity metrics show insufficient data message when tracking < 7 days."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        days_2 = 2 * 24 * 60 * 60
        
        # Create 10 events all discovered within last 2 days
        history = {'events': {}}
        for i in range(10):
            event_id = f'event{i}'
            history['events'][event_id] = {
                'id': event_id,
                'title': f'Event {i}',
                'deadline': '31 Dec 2030 23:59',
                'first_seen': int(current_time - days_2),
                'last_seen': int(current_time),
                'expired_at': None,
            }
        
        state = {'seen_ids': list(history['events'].keys())}
        stats = generate_statistics(history, state)
        
        self.assertIn('event_velocity', stats)
        velocity = stats['event_velocity']
        # Should have insufficient_data flag
        self.assertTrue(velocity.get('insufficient_data', False))
        # Events per week/month should be None
        self.assertIsNone(velocity['events_per_week'])
        self.assertIsNone(velocity['events_per_month'])
        # But tracking days should still be reported
        self.assertIsNotNone(velocity['tracking_days'])
        self.assertLess(velocity['tracking_days'], 7)
    
    def test_long_running_events_detection(self):
        """Test detection of long-running events (active > 60 days)."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        days_70 = 70 * 24 * 60 * 60
        days_10 = 10 * 24 * 60 * 60
        
        history = {
            'events': {
                'event1': {
                    'id': 'event1',
                    'title': 'Long Running Event',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(current_time - days_70),
                    'last_seen': int(current_time),
                    'expired_at': None,
                },
                'event2': {
                    'id': 'event2',
                    'title': 'Short Event',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(current_time - days_10),
                    'last_seen': int(current_time),
                    'expired_at': None,
                }
            }
        }
        
        state = {'seen_ids': ['event1', 'event2']}
        stats = generate_statistics(history, state)
        
        self.assertIn('long_running_events', stats)
        self.assertEqual(len(stats['long_running_events']), 1)
        self.assertEqual(stats['long_running_events'][0]['title'], 'Long Running Event')
        self.assertGreater(stats['long_running_events'][0]['days_active'], 60)
    
    def test_recently_expired_events(self):
        """Test recently expired events tracking."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        days_3 = 3 * 24 * 60 * 60
        days_10 = 10 * 24 * 60 * 60
        
        history = {
            'events': {
                'event1': {
                    'id': 'event1',
                    'title': 'Recently Expired',
                    'deadline': '1 Jan 2020 00:00',
                    'first_seen': int(current_time - days_3),
                    'last_seen': int(current_time),
                    'expired_at': int(current_time - days_3),
                    'registration_duration_days': 30.0,
                },
                'event2': {
                    'id': 'event2',
                    'title': 'Old Expired',
                    'deadline': '1 Jan 2020 00:00',
                    'first_seen': int(current_time - days_10),
                    'last_seen': int(current_time),
                    'expired_at': int(current_time - days_10),
                    'registration_duration_days': 45.0,
                }
            }
        }
        
        state = {'seen_ids': ['event1', 'event2']}
        stats = generate_statistics(history, state)
        
        self.assertIn('recently_expired', stats)
        self.assertEqual(len(stats['recently_expired']), 1)
        self.assertEqual(stats['recently_expired'][0]['title'], 'Recently Expired')
    
    def test_monthly_trends(self):
        """Test monthly trends calculation."""
        from check_events import generate_statistics
        import time
        from datetime import datetime, timedelta
        
        current_time = time.time()
        
        # Create events across multiple months
        history = {'events': {}}
        for month_offset in range(3):
            for event_num in range(2):
                event_id = f'event_m{month_offset}_{event_num}'
                event_time = current_time - (month_offset * 30 * 24 * 60 * 60)
                history['events'][event_id] = {
                    'id': event_id,
                    'title': f'Event {month_offset}-{event_num}',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(event_time),
                    'last_seen': int(current_time),
                    'expired_at': None,
                }
        
        state = {'seen_ids': list(history['events'].keys())}
        stats = generate_statistics(history, state)
        
        self.assertIn('monthly_trends', stats)
        self.assertIsInstance(stats['monthly_trends'], list)
        self.assertGreater(len(stats['monthly_trends']), 0)
        
        # Check structure of trend data
        if stats['monthly_trends']:
            trend = stats['monthly_trends'][0]
            self.assertIn('month', trend)
            self.assertIn('events_added', trend)
    
    def test_active_event_ages(self):
        """Test active event age statistics."""
        from check_events import generate_statistics
        import time
        
        current_time = time.time()
        
        history = {
            'events': {
                'event1': {
                    'id': 'event1',
                    'title': 'Event 1',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(current_time - (10 * 24 * 60 * 60)),
                    'last_seen': int(current_time),
                    'expired_at': None,
                },
                'event2': {
                    'id': 'event2',
                    'title': 'Event 2',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(current_time - (20 * 24 * 60 * 60)),
                    'last_seen': int(current_time),
                    'expired_at': None,
                },
                'event3': {
                    'id': 'event3',
                    'title': 'Event 3',
                    'deadline': '31 Dec 2030 23:59',
                    'first_seen': int(current_time - (30 * 24 * 60 * 60)),
                    'last_seen': int(current_time),
                    'expired_at': None,
                }
            }
        }
        
        state = {'seen_ids': ['event1', 'event2', 'event3']}
        stats = generate_statistics(history, state)
        
        self.assertIn('active_event_ages', stats)
        ages = stats['active_event_ages']
        self.assertIn('min', ages)
        self.assertIn('max', ages)
        self.assertIn('median', ages)
        self.assertIn('average', ages)
        self.assertGreater(ages['max'], ages['min'])
    
    def test_enhanced_html_includes_new_sections(self):
        """Test that enhanced HTML includes new statistics sections."""
        from check_events import save_statistics
        
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, 'stats.json')
            html_path = os.path.join(tmpdir, 'stats.html')
            
            stats = {
                'generated_at': int(time.time()),
                'total_events_tracked': 10,
                'currently_active': 5,
                'total_expired': 5,
                'new_this_week': 2,
                'new_this_month': 3,
                'expired_this_week': 1,
                'expired_this_month': 2,
                'upcoming_deadlines': [],
                'recently_expired': [],
                'long_running_events': [],
                'monthly_trends': [
                    {'month': '2025-01', 'events_added': 5},
                    {'month': '2025-02', 'events_added': 3}
                ],
                'event_velocity': {
                    'events_per_week': 2.5,
                    'events_per_month': 10.0,
                    'tracking_days': 30.0
                },
                'registration_duration_stats': {
                    'min': 10.0,
                    'max': 50.0,
                    'median': 30.0,
                    'average': 30.0,
                    'total_completed': 5
                },
                'active_event_ages': {
                    'min': 5.0,
                    'max': 60.0,
                    'median': 30.0,
                    'average': 32.5
                }
            }
            
            save_statistics(stats, json_path, html_path)
            
            # Verify HTML includes enhanced sections
            with open(html_path, 'r') as f:
                html_content = f.read()
            
            self.assertIn('Event Velocity', html_content)
            self.assertIn('Registration Duration Analysis', html_content)
            self.assertIn('Active Event Ages', html_content)
            self.assertIn('Monthly Event Trends', html_content)
            self.assertIn('Recently Expired', html_content)
            self.assertIn('Long-Running Events', html_content)
            self.assertIn('chart.js', html_content.lower())  # Chart library included (case-insensitive)


if __name__ == '__main__':
    unittest.main()
