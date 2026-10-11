import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from subagent_orchestrator import parallel_analysis
class FakeModel:
 def __init__(self):self.prompts=[]
 def response(self,prompt,model):
  self.prompts.append(prompt)
  return "Synthesis" if "Combine the following" in prompt else "Independent findings"
class ParallelTests(unittest.TestCase):
 def test_parallel_analysis_results_and_final_synthesis(self):
  fake=FakeModel();activity=[]
  result=parallel_analysis(fake,"mock","Develop a local app",activity.append)
  self.assertEqual(result["worker_count"],3)
  self.assertEqual(result["answer"],"Synthesis")
  self.assertEqual(len(activity),3)
  self.assertEqual(len(fake.prompts),4)
  self.assertIn("do not",fake.prompts[0].lower())
 def test_invalid_input(self):
  with self.assertRaises(ValueError):
   parallel_analysis(FakeModel(),"mock","")
if __name__=="__main__":unittest.main()
