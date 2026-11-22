import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from core.video_workflows import build_core_wan_graph, validate_graph, video_capabilities, core_video_output
class VideoTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cp=Path((ROOT/'scratch/current_native_video_checkpoint.txt').read_text().strip());cls.info=json.loads((cp/'object_info_before.local.json').read_text())
 def test_wan_uses_actual_core_contract_and_h264_output(self):
  graph=build_core_wan_graph('A blue cube slowly rotating',self.info,width=512,height=384,length=49,steps=6)
  self.assertEqual(validate_graph(graph,self.info),[])
  names={n['class_type'] for n in graph.values()};self.assertTrue({'UNETLoader','CLIPLoader','VAELoader','KSampler','CreateVideo','SaveVideo'}<=names);self.assertNotIn('VHS_VideoCombine',names)
  out=next(n for n in graph.values() if n['class_type']=='SaveVideo');self.assertEqual(out['inputs']['format'],'mp4');self.assertEqual(out['inputs']['codec'],'h264')
 def test_capabilities_never_mark_missing_encoder_or_model_ready(self):
  self.assertTrue(video_capabilities(self.info)['wan_t2v']['ready'])
  broken={k:v for k,v in self.info.items() if k!='SaveVideo'};self.assertFalse(video_capabilities(broken)['wan_t2v']['ready'])
  broken=json.loads(json.dumps(self.info));broken['UNETLoader']['input']['required']['unet_name'][0]=[];self.assertFalse(video_capabilities(broken)['wan_t2v']['ready'])
 def test_unavailable_graph_rejected_before_any_submission(self):
  with self.assertRaises(ValueError):build_core_wan_graph('test',{},length=49)
  with self.assertRaises(ValueError):build_core_wan_graph('test',self.info,length=50)
  with self.assertRaises(ValueError):build_core_wan_graph('test',self.info,width=513)
 def test_legacy_video_output_converts_without_changing_frame_source(self):
  original={'8':{'class_type':'VAEDecode','inputs':{'samples':['1',0],'vae':['2',0]}},'41':{'class_type':'VHS_VideoCombine','inputs':{'images':['8',0],'frame_rate':16,'filename_prefix':'AIBS_Test','format':'video/h264-mp4'}}}
  graph=core_video_output(original);self.assertEqual(graph['41']['class_type'],'SaveVideo');create=next(n for n in graph.values() if n['class_type']=='CreateVideo');self.assertEqual(create['inputs']['images'],['8',0]);self.assertEqual(original['41']['class_type'],'VHS_VideoCombine')
if __name__=='__main__':unittest.main()
