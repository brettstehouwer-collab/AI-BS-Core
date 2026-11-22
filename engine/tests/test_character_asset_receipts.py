import unittest,uuid
from native_studio.game_engine.asset_view import AssetView

class CharacterReceiptTests(unittest.TestCase):
    def row(self):
        return dict(asset_id=str(uuid.uuid4()),name='Synthetic rig',sha256='1'*64,
            triangles=120000,materials=2,kind='character',image_count=1,
            decoded_image_bytes=20,decoded_bytes=100000,joint_count=64,
            clip_count=4,vertices=262144)

    def test_owned_character_counts_are_preserved(self):
        r=self.row();value=AssetView._rows({'assets':[r]})[0]
        for key in ('kind','joint_count','clip_count','vertices'):
            self.assertEqual(value[key],r[key])

    def test_character_limits_reject(self):
        for key,value in (('joint_count',0),('joint_count',65),('joint_count',True),
                ('clip_count',9),('clip_count',-1),('vertices',262145),
                ('vertices',0),('triangles',524289),('decoded_bytes',64*1024*1024+1)):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                r=self.row();r[key]=value;AssetView._rows({'assets':[r]})

    def test_legacy_geometry_limit_retained(self):
        r=self.row();r['kind']='mesh';r['image_count']=r['decoded_image_bytes']=0
        with self.assertRaises(ValueError):AssetView._rows({'assets':[r]})

    def test_character_uses_chapter_preview(self):
        self.assertFalse(AssetView._preview_supported(object(),self.row()))

if __name__=='__main__':unittest.main()
