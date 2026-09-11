"""Exercise question navigation with an isolated temporary database."""
import os
import tempfile
from pathlib import Path

os.environ['CLOUD_CHAOS_DATA_DIR'] = tempfile.mkdtemp(prefix='cloud-mobile-qa-')
from streamlit.testing.v1 import AppTest

at = AppTest.from_file(str(Path(__file__).with_name('app.py')), default_timeout=30).run()
at.text_input(key='reg_name').input('Mobile QA')
at.text_input(key='reg_company').input('Local test')
at.button[0].click().run()
assert not at.exception
# AppTest retains the prior form tree across st.rerun; settle the new screen.
at.session_state['reg_name'] = 'Mobile QA'
at.session_state['reg_company'] = 'Local test'
at.run()
cards = at.session_state['game_cards']
at.button(key='question_nav_2').click().run()
assert at.session_state['active_pain'] == 2
at.button(key='right_2').click().run()
assert at.session_state['active_pain'] == 0
at.button(key='question_nav_2').click().run()
at.button(key='wrong_2').click().run()
assert at.session_state['selections'][cards[2]['orig_idx']]['answer'] is False
for i, card in enumerate(cards):
    at.button(key=f'question_nav_{i}').click().run()
    at.button(key=('right_' if card['is_right'] else 'wrong_') + str(i)).click().run()
at.button(key='fab_submit').click().run()
assert not at.exception
assert at.session_state['score'] == 6
at.button(key='res_lb').click().run()
assert not at.exception
assert at.session_state['screen'] == 'leaderboard'
print('PASS: navigation, auto-advance, answer revision, 6/6 scoring, leaderboard')
