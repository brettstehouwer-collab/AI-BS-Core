import copy
import unittest


class PreferenceContracts(unittest.TestCase):
    def api(self):
        from native_studio import broadcast_preferences
        return broadcast_preferences

    def test_default_keeps_audio_off_and_preserves_original_shared_output(self):
        preferences = self.api().defaults()
        self.assertFalse(preferences['audio']['mic']['enabled'])
        self.assertFalse(preferences['audio']['desktop_audio']['enabled'])
        self.assertEqual(preferences['mode'], 'shared')

    def test_maximum_profiles_are_independent_and_fit_100_mbps(self):
        preferences = self.api().maximum_preferences(100)
        self.api().validate(preferences)
        profiles = preferences['outputs']
        self.assertEqual(profiles['twitch']['video_kbps'], 6000)
        self.assertEqual(profiles['kick']['video_kbps'], 8000)
        self.assertGreater(profiles['youtube']['video_kbps'], profiles['twitch']['video_kbps'])
        self.assertLess(self.api().required_upload_mbps(preferences), 100)

    def test_cannot_enable_maximum_beyond_upload_capacity(self):
        preferences = self.api().maximum_preferences(100)
        preferences['upload_mbps'] = 20
        with self.assertRaises(ValueError): self.api().validate(preferences)

    def test_untrusted_paths_and_credentials_are_not_preferences(self):
        preferences = self.api().maximum_preferences(100)
        for key, value in [('url', 'not-a-destination'), ('key', 'synthetic')]:
            invalid = copy.deepcopy(preferences)
            invalid['outputs']['youtube'][key] = value
            with self.assertRaises(ValueError): self.api().validate(invalid)
        preferences['audio']['mic']['gain'] = float('nan')
        with self.assertRaises(ValueError): self.api().validate(preferences)
