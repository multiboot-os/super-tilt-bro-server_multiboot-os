import base64
import copy
import json
import logging as log
import os.path
import requests
import subprocess

#
# Working structures
#

_replay_dir = None
_db_file = None
_bmov_to_fm2 = None
_login_server = None

replay_db = {
	'replays': {},
}

#
# Internal utilities
#

def _sync_db():
	global _db_file, replay_db
	if _db_file is not None:
		tmp_db_path = '{}.tmp'.format(_db_file)
		with open(tmp_db_path, 'w') as tmp_db:
			json.dump(replay_db, tmp_db)
		os.replace(tmp_db_path, _db_file)

def get_fm2_path(game):
	global _replay_dir
	return '{}/{}.fm2'.format(_replay_dir, game)

def _get_user_name(user_id):
	global _login_server

	if _login_server is None:
		return None

	if user_id < 0x80000000:
		return None

	resp = requests.get('http://{}:{}/api/login/user_name/{}'.format(_login_server['addr'], _login_server['port'], user_id))
	if resp.status_code != 200:
		log.error('bad status code for resoultion of user {}: {}'.format(user_id, resp.status_code))
		return None
	user_name = json.loads(resp.text)

	if user_name is None:
		return None
	if not isinstance(user_name, str):
		raise Exception('bad response type: {}'.format(user_name))
	if len(user_name) < 3 or len(user_name) > 16:
		raise Exception('unvalid name: "{}"'.format(user_name))
	return user_name

#
# Public API
#

def load(db_file, replay_dir, bmov_to_fm2, login_server):
	global _db_file, _replay_dir, _bmov_to_fm2, _login_server, replay_db

	_replay_dir = replay_dir
	if not os.path.isdir(replay_dir):
		os.makedirs(replay_dir, mode=0o666, exist_ok=True)

	_bmov_to_fm2 = bmov_to_fm2
	if not os.path.isfile(bmov_to_fm2):
		raise Exception('unable to find bmov_to_fm2 at "{}"'.format(bmov_to_fm2))

	_login_server = copy.deepcopy(login_server)

	_db_file = db_file
	if db_file is not None and os.path.isfile(db_file):
		with open(db_file, 'r') as f:
			replay_db = json.load(f)

def push_games(games_info):
	global replay_db, _replay_dir, _bmov_to_fm2

	# Record games
	for game_info in games_info:
		# Check game consistency
		mandatory_fields = ['bmov', 'game_server', 'game', 'begin', 'end', 'client_a', 'client_b', 'character_a', 'character_b', 'character_a_palette', 'character_b_palette']
		for field in mandatory_fields:
			if field not in game_info:
				raise Exception('invalid game info format, missing "{}" field'.format(field))

		if game_info['game'] in replay_db['replays']:
			raise Exception('pushed already present game "{}"'.format(game_info['game']))

		# Save bmov file
		bmov_path = '{}/{}.bmov'.format(_replay_dir, game_info['game'])
		bmov_data = base64.b64decode(game_info['bmov'])
		with open(bmov_path, 'wb') as bmov_file:
			bmov_file.write(bmov_data)

		# Convert bmov to fm2
		fm2_path = get_fm2_path(game_info['game'])
		cmd = [
			_bmov_to_fm2,
			'--palette-a', str(game_info['character_a_palette']),
			'--palette-b', str(game_info['character_b_palette']),
			bmov_path
		]
		fm2_data = subprocess.run(cmd, check=True, encoding='utf-8', stdout=subprocess.PIPE).stdout
		with open(fm2_path, 'w') as fm2_file:
			fm2_file.write(fm2_data)

		# Delete bmov file
		os.remove(bmov_path)

		# Add replay entry in DB
		replay_db['replays'][game_info['game']] = {
			'game': game_info['game'],
			'begin': game_info['begin'],
			'end': game_info['end'],
			'player_a': _get_user_name(game_info['client_a']),
			'player_b': _get_user_name(game_info['client_b']),
			'character_a': game_info['character_a'],
			'character_b': game_info['character_b'],
			'character_a_palette': game_info['character_a_palette'],
			'character_b_palette': game_info['character_b_palette'],
			'stage': game_info['stage'],
			'game_server': game_info['game_server']
		}

	# Update DB file
	_sync_db()

def get_games_list():
	global replay_db
	return sorted(
		[replay_db['replays'][game] for game in replay_db['replays']],
		key=lambda x: x['begin']
	)[-50:]

def get_game_info(game):
	global replay_db
	return replay_db['replays'][game]

def get_fm2(game):
	with open(get_fm2_path(game), 'r') as fm2_file:
		return fm2_file.read()
