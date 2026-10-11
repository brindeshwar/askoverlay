import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import suggest  # noqa: E402


def test_json_array_is_parsed():
    reply = '["How do I save?", "How do I close this?"]'
    assert suggest.parse_questions(reply, 6) == ["How do I save?", "How do I close this?"]


def test_code_fences_and_chatter_around_the_array_are_ignored():
    reply = 'Here you go:\n```json\n["How do I zoom in?", "Where do I sign out?"]\n```\nHope that helps!'
    assert suggest.parse_questions(reply, 6) == ["How do I zoom in?", "Where do I sign out?"]


def test_bullet_list_fallback_when_there_is_no_json():
    reply = "1. How do I save my work?\n2) How do I print this?\n- Where is the search box?\nnot a question"
    assert suggest.parse_questions(reply, 6) == ["How do I save my work?", "How do I print this?", "Where is the search box?"]


def test_duplicates_blank_and_non_string_items_are_dropped():
    reply = '["How do I save?", "how do i save?", "", 42, null, "  How do I print?  "]'
    assert suggest.parse_questions(reply, 6) == ["How do I save?", "How do I print?"]


def test_overlong_questions_are_dropped_and_the_limit_is_respected():
    long_one = "How do I " + "really " * 40 + "save?"
    reply = '["' + long_one + '", "Q1?", "Q2?", "Q3?"]'
    assert suggest.parse_questions(reply, 2) == ["Q1?", "Q2?"]


def test_whitespace_inside_a_question_is_collapsed():
    assert suggest.parse_questions('["How   do I\\n save?"]', 6) == ["How do I save?"]


def test_garbage_gives_an_empty_list_not_a_crash():
    assert suggest.parse_questions("I'm sorry, I can't help with that.", 6) == []
    assert suggest.parse_questions("[not json at all", 6) == []
