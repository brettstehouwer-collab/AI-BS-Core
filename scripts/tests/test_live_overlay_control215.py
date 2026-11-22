import unittest


class OverlayControlContracts(unittest.TestCase):
    def api(self):
        from native_studio import live_overlay_control
        return live_overlay_control

    def test_default_is_disabled_and_uses_one_explicit_chat_channel(self):
        config=self.api().defaults()
        self.assertFalse(config['enabled'])
        self.assertEqual(config['channel'], 'brettstehouwer')
        self.assertEqual(self.api().validate(config), config)

    def test_settings_cannot_smuggle_paths_keys_or_arbitrary_urls(self):
        for key in ('url','token','model_path'):
            config=self.api().defaults(); config[key]='synthetic'
            with self.assertRaises(ValueError): self.api().validate(config)
        config=self.api().defaults(); config['channel']='channel\r\nPRIVMSG #x :bad'
        with self.assertRaises(ValueError): self.api().validate(config)

    def test_control_commands_cannot_fabricate_game_achievements(self):
        self.assertTrue(self.api().valid_command({'version':1,'id':'a'*32,'kind':'hype'}))
        self.assertFalse(self.api().valid_command({'version':1,'id':'a'*32,'kind':'victory'}))
        self.assertFalse(self.api().valid_command({'version':1,'id':'a'*32,'kind':'hype','text':'arbitrary'}))
