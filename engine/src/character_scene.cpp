#include <aibs/character_scene.hpp>
#include <algorithm>
#include <cmath>
#include <limits>
#include <set>
#include <stdexcept>

namespace aibs {
namespace {
constexpr double matrix_bound=1e12;
using D3=std::array<double,3>;
void need(bool value,const char* message){if(!value)throw std::invalid_argument(message);}
bool bounded(float v,double limit=1e6){return std::isfinite(v)&&std::abs(static_cast<double>(v))<=limit;}
bool bounded(Vec3 v,double limit=1e6){return bounded(v.x,limit)&&bounded(v.y,limit)&&bounded(v.z,limit);}
bool unit(float v){return std::isfinite(v)&&v>=0&&v<=1;}
std::size_t add(std::size_t a,std::size_t b){need(b<=std::numeric_limits<std::size_t>::max()-a,"Character byte count overflow");return a+b;}
std::size_t multiply(std::size_t a,std::size_t b){need(!a||b<=std::numeric_limits<std::size_t>::max()/a,"Character byte count overflow");return a*b;}
float number(double d){need(std::isfinite(d)&&std::abs(d)<=matrix_bound,"Character transform overflow");return static_cast<float>(d);}
std::array<double,4> quaternion(Quaternion q){
 need(bounded(q.x,2)&&bounded(q.y,2)&&bounded(q.z,2)&&bounded(q.w,2),"Invalid character rotation");
 const double n=static_cast<double>(q.x)*q.x+static_cast<double>(q.y)*q.y+static_cast<double>(q.z)*q.z+static_cast<double>(q.w)*q.w;
 need(std::abs(n-1)<=1e-4,"Character rotation must be a unit quaternion");const auto length=std::sqrt(n);
 return {q.x/length,q.y/length,q.z/length,q.w/length};
}
void transform(const CharacterJointTransform& t){
 need(bounded(t.translation),"Character local translation outside bounds");(void)quaternion(t.rotation);
 need(bounded(t.scale,1000)&&t.scale.x>=.001f&&t.scale.y>=.001f&&t.scale.z>=.001f,"Character scale must be positive and nonsingular");
}
double determinant(const CharacterMatrix& a){return static_cast<double>(a[0])*(static_cast<double>(a[5])*a[10]-static_cast<double>(a[6])*a[9])-static_cast<double>(a[1])*(static_cast<double>(a[4])*a[10]-static_cast<double>(a[6])*a[8])+static_cast<double>(a[2])*(static_cast<double>(a[4])*a[9]-static_cast<double>(a[5])*a[8]);}
void affine(const CharacterMatrix& a){
 for(float v:a)need(bounded(v,matrix_bound),"Invalid character matrix");
 need(a[3]==0&&a[7]==0&&a[11]==0&&a[15]==1,"Character matrix must be affine row-vector form");
 double scale=0;for(unsigned row=0;row<3;++row)for(unsigned column=0;column<3;++column)scale=std::max(scale,std::abs(static_cast<double>(a[row*4+column])));
 const auto d=determinant(a);need(scale>0&&std::isfinite(d)&&d/(scale*scale*scale)>1e-12,"Character matrix must be nonsingular and orientation-preserving");
}
CharacterMatrix product(const CharacterMatrix& a,const CharacterMatrix& b){CharacterMatrix result{};for(unsigned row=0;row<4;++row)for(unsigned column=0;column<4;++column){double value=0;for(unsigned k=0;k<4;++k)value+=static_cast<double>(a[row*4+k])*b[k*4+column];result[row*4+column]=number(value);}return result;}
CharacterMatrix normal_matrix(const CharacterMatrix& a){
 affine(a);const double d=determinant(a);CharacterMatrix n=character_identity_matrix;
 n[0]=number((static_cast<double>(a[5])*a[10]-static_cast<double>(a[6])*a[9])/d);
 n[1]=number((static_cast<double>(a[6])*a[8]-static_cast<double>(a[4])*a[10])/d);
 n[2]=number((static_cast<double>(a[4])*a[9]-static_cast<double>(a[5])*a[8])/d);
 n[4]=number((static_cast<double>(a[2])*a[9]-static_cast<double>(a[1])*a[10])/d);
 n[5]=number((static_cast<double>(a[0])*a[10]-static_cast<double>(a[2])*a[8])/d);
 n[6]=number((static_cast<double>(a[1])*a[8]-static_cast<double>(a[0])*a[9])/d);
 n[8]=number((static_cast<double>(a[1])*a[6]-static_cast<double>(a[2])*a[5])/d);
 n[9]=number((static_cast<double>(a[2])*a[4]-static_cast<double>(a[0])*a[6])/d);
 n[10]=number((static_cast<double>(a[0])*a[5]-static_cast<double>(a[1])*a[4])/d);return n;
}
D3 point(Vec3 v,const CharacterMatrix& a,bool position){return {static_cast<double>(v.x)*a[0]+static_cast<double>(v.y)*a[4]+static_cast<double>(v.z)*a[8]+(position?a[12]:0),static_cast<double>(v.x)*a[1]+static_cast<double>(v.y)*a[5]+static_cast<double>(v.z)*a[9]+(position?a[13]:0),static_cast<double>(v.x)*a[2]+static_cast<double>(v.y)*a[6]+static_cast<double>(v.z)*a[10]+(position?a[14]:0)};}
Vec3 vector(D3 v){for(auto n:v)need(std::isfinite(n)&&std::abs(n)<=std::numeric_limits<float>::max(),"Character vertex transform overflow");return {static_cast<float>(v[0]),static_cast<float>(v[1]),static_cast<float>(v[2])};}
double length_squared(D3 v){return v[0]*v[0]+v[1]*v[1]+v[2]*v[2];}
void counts(const CharacterMesh& m){need(!m.joints.empty()&&m.joints.size()<=character_maximum_joints,"Character joint count outside1..64");need(m.vertices.size()<=character_maximum_vertices&&m.indices.size()<=character_maximum_indices&&m.clips.size()<=character_maximum_clips,"Character resource count exceeds bounds");}
void skeleton(const CharacterMesh& m){
 need(!m.joints.empty()&&m.joints.size()<=character_maximum_joints,"Character joint count outside1..64");std::array<CharacterMatrix,character_maximum_joints> global{};
 for(std::size_t i=0;i<m.joints.size();++i){const auto& j=m.joints[i];need(i==0?j.parent==-1:j.parent>=0&&static_cast<std::size_t>(j.parent)<i,"Character parents must form one topologically ordered tree");
  auto local=character_transform_matrix(j.bind_local);global[i]=i?product(local,global[static_cast<std::size_t>(j.parent)]):local;affine(global[i]);affine(j.inverse_bind);
  const auto identity=product(j.inverse_bind,global[i]);for(std::size_t k=0;k<16;++k)need(std::abs(identity[k]-character_identity_matrix[k])<=5e-4f,"Character inverse bind disagrees with global bind transform");
 }
}
void vertex(const CharacterVertex& v,std::size_t joints){
 need(bounded(v.position)&&bounded(v.normal)&&(v.normal.x!=0||v.normal.y!=0||v.normal.z!=0)&&bounded(v.u)&&bounded(v.v),"Invalid character position, normal or UV");
 need(std::abs(static_cast<double>(v.normal.x)*v.normal.x+static_cast<double>(v.normal.y)*v.normal.y+static_cast<double>(v.normal.z)*v.normal.z-1)<=1e-4,"Character vertex normal must be unit length");
 need(unit(v.color.x)&&unit(v.color.y)&&unit(v.color.z)&&std::isfinite(v.emission)&&v.emission>=0&&v.emission<=16,"Invalid character color/emission");
 double sum=0;for(unsigned i=0;i<4;++i){need(v.joints[i]<joints&&unit(v.weights[i]),"Invalid character joint index/weight");sum+=v.weights[i];}need(std::abs(sum-1)<=1e-5,"Character weights must sum to one");
}
void clip_header(const CharacterClip& c,std::size_t joints){
 need(!c.name.empty()&&c.name.size()<=64&&std::none_of(c.name.begin(),c.name.end(),[](unsigned char ch){return ch<32||ch==127;}),"Invalid character clip name");
 need(std::isfinite(c.duration_seconds)&&c.duration_seconds>0&&c.duration_seconds<=3600&&c.frame_count>0&&c.frame_count<=character_maximum_clip_frames,"Invalid character clip duration/frame count");
 need(c.samples.size()==multiply(c.frame_count,joints),"Character baked sample count mismatch");
}
void sample(const CharacterJointTransform& t,const CharacterJointTransform& root,bool is_root){transform(t);if(is_root)need(t.translation==root.translation,"Character clip contains root translation; expected in-place animation");}
Quaternion interpolate(Quaternion a,Quaternion b,double alpha){
 const auto p=quaternion(a);auto q=quaternion(b);double dot=0;for(unsigned i=0;i<4;++i)dot+=p[i]*q[i];if(dot<0){for(auto& n:q)n=-n;dot=-dot;}dot=std::clamp(dot,-1.,1.);
 double first=1-alpha,second=alpha;if(dot<.9995){const auto angle=std::acos(dot),denominator=std::sin(angle);first=std::sin((1-alpha)*angle)/denominator;second=std::sin(alpha*angle)/denominator;}
 std::array<double,4> r{};double norm=0;for(unsigned i=0;i<4;++i){r[i]=first*p[i]+second*q[i];norm+=r[i]*r[i];}need(norm>0&&std::isfinite(norm),"Character quaternion interpolation failed");const auto inverse=1/std::sqrt(norm);
 return {static_cast<float>(r[0]*inverse),static_cast<float>(r[1]*inverse),static_cast<float>(r[2]*inverse),static_cast<float>(r[3]*inverse)};
}
Vec3 interpolate(Vec3 a,Vec3 b,double alpha){return {number((1-alpha)*a.x+alpha*b.x),number((1-alpha)*a.y+alpha*b.y),number((1-alpha)*a.z+alpha*b.z)};}
void pose(const CharacterMesh& m,const CharacterPose& p){need(p.joint_count==m.joints.size(),"Character pose skeleton count mismatch");for(std::size_t i=0;i<p.joint_count;++i)transform(p.local[i]);}
}

CharacterMeshCost character_mesh_cost(const CharacterMesh& m){
 counts(m);CharacterMeshCost c;c.gpu_vertex_bytes=multiply(m.vertices.size(),sizeof(CharacterVertex));c.gpu_index_bytes=multiply(m.indices.size(),sizeof(std::uint32_t));
 c.payload_bytes=add(128,add(c.gpu_vertex_bytes,add(c.gpu_index_bytes,multiply(m.joints.size(),108))));
 c.decoded_bytes=add(sizeof(CharacterMesh),add(multiply(m.vertices.capacity(),sizeof(CharacterVertex)),add(multiply(m.indices.capacity(),sizeof(std::uint32_t)),add(multiply(m.joints.capacity(),sizeof(CharacterJoint)),multiply(m.clips.capacity(),sizeof(CharacterClip))))));
 for(const auto& clip:m.clips){const auto bytes=multiply(clip.samples.size(),40);c.animation_bytes=add(c.animation_bytes,bytes);c.payload_bytes=add(c.payload_bytes,add(32,add(add(clip.name.size(),1),bytes)));c.decoded_bytes=add(c.decoded_bytes,add(add(clip.name.capacity(),1),multiply(clip.samples.capacity(),sizeof(CharacterJointTransform))));}return c;
}
void validate_character_mesh(const CharacterMesh& m){
 counts(m);need(!m.vertices.empty()&&!m.indices.empty()&&m.indices.size()%3==0,"Character requires indexed triangles");const auto cost=character_mesh_cost(m);
 need(cost.payload_bytes<=character_maximum_payload_bytes&&cost.decoded_bytes<=character_maximum_decoded_bytes,"Character payload/decoded storage exceeds budget");skeleton(m);
 for(const auto& v:m.vertices)vertex(v,m.joints.size());for(auto index:m.indices)need(index<m.vertices.size(),"Character triangle index outside vertex array");
 std::set<std::string> names;for(const auto& c:m.clips){clip_header(c,m.joints.size());need(names.insert(c.name).second,"Duplicate character clip name");for(std::size_t i=0;i<c.samples.size();++i)sample(c.samples[i],m.joints[0].bind_local,i%m.joints.size()==0);}
}
CharacterMatrix character_transform_matrix(const CharacterJointTransform& t){
 transform(t);const auto q=quaternion(t.rotation);const auto x=q[0],y=q[1],z=q[2],w=q[3];CharacterMatrix m=character_identity_matrix;
 m[0]=number(t.scale.x*(1-2*(y*y+z*z)));m[1]=number(t.scale.x*2*(x*y+z*w));m[2]=number(t.scale.x*2*(x*z-y*w));
 m[4]=number(t.scale.y*2*(x*y-z*w));m[5]=number(t.scale.y*(1-2*(x*x+z*z)));m[6]=number(t.scale.y*2*(y*z+x*w));
 m[8]=number(t.scale.z*2*(x*z+y*w));m[9]=number(t.scale.z*2*(y*z-x*w));m[10]=number(t.scale.z*(1-2*(x*x+y*y)));
 m[12]=t.translation.x;m[13]=t.translation.y;m[14]=t.translation.z;affine(m);return m;
}
CharacterPose character_bind_pose(const CharacterMesh& m){skeleton(m);CharacterPose p;p.joint_count=static_cast<std::uint32_t>(m.joints.size());for(std::size_t i=0;i<m.joints.size();++i)p.local[i]=m.joints[i].bind_local;return p;}
CharacterPose sample_character_clip(const CharacterMesh& m,std::size_t clip_index,double seconds){
 skeleton(m);need(clip_index<m.clips.size(),"Character animation index outside clips");need(std::isfinite(seconds)&&seconds>=0,"Character animation time must be finite/nonnegative");const auto& c=m.clips[clip_index];clip_header(c,m.joints.size());
 const auto time=c.looping?std::fmod(seconds,c.duration_seconds):std::min(seconds,static_cast<double>(c.duration_seconds));const auto frame=time/c.duration_seconds*(c.frame_count-1);
 const auto first=static_cast<std::size_t>(std::floor(frame)),second=std::min(first+1,static_cast<std::size_t>(c.frame_count-1));const auto alpha=frame-static_cast<double>(first);
 CharacterPose result;result.joint_count=static_cast<std::uint32_t>(m.joints.size());for(std::size_t j=0;j<m.joints.size();++j){const auto& a=c.samples[first*m.joints.size()+j];const auto& b=c.samples[second*m.joints.size()+j];sample(a,m.joints[0].bind_local,j==0);sample(b,m.joints[0].bind_local,j==0);result.local[j]={interpolate(a.translation,b.translation,alpha),interpolate(a.rotation,b.rotation,alpha),interpolate(a.scale,b.scale,alpha)};}return result;
}
CharacterSkinPalette character_skin_palette(const CharacterMesh& m,const CharacterPose& p){
 skeleton(m);pose(m,p);CharacterSkinPalette result;result.joint_count=p.joint_count;result.skin.fill(character_identity_matrix);result.normal.fill(character_identity_matrix);std::array<CharacterMatrix,character_maximum_joints> global{};
 for(std::size_t i=0;i<p.joint_count;++i){auto local=character_transform_matrix(p.local[i]);global[i]=i?product(local,global[static_cast<std::size_t>(m.joints[i].parent)]):local;result.skin[i]=product(m.joints[i].inverse_bind,global[i]);result.normal[i]=normal_matrix(result.skin[i]);}return result;
}
CharacterPose blend_character_poses(const CharacterPose& a,const CharacterPose& b,float factor){
 need(a.joint_count>0&&a.joint_count<=character_maximum_joints&&a.joint_count==b.joint_count,"Character pose joint count mismatch");
 need(std::isfinite(factor)&&factor>=0.f&&factor<=1.f,"Blend factor must be finite and within [0, 1]");
 CharacterPose result;result.joint_count=a.joint_count;
 const double alpha=static_cast<double>(factor);
 for(std::size_t i=0;i<a.joint_count;++i){
  result.local[i]={interpolate(a.local[i].translation,b.local[i].translation,alpha),
                   interpolate(a.local[i].rotation,b.local[i].rotation,alpha),
                   interpolate(a.local[i].scale,b.local[i].scale,alpha)};
 }
 return result;
}
void validate_character_instance(const CharacterMesh& m,const CharacterInstance& instance){(void)character_skin_palette(m,instance.pose);(void)normal_matrix(instance.world);need(unit(instance.tint.x)&&unit(instance.tint.y)&&unit(instance.tint.z)&&unit(instance.opacity)&&std::isfinite(instance.emission)&&instance.emission>=0&&instance.emission<=16,"Invalid character instance appearance");}
CharacterSkinnedVertex character_skin_vertex(const CharacterVertex& v,const CharacterSkinPalette& palette,const CharacterMatrix& world){
 need(palette.joint_count>0&&palette.joint_count<=character_maximum_joints,"Invalid character skin palette count");vertex(v,palette.joint_count);affine(world);D3 position{},normal{};double normal_scale=0;
 for(unsigned slot=0;slot<4;++slot){if(v.weights[slot]==0)continue;const auto joint=v.joints[slot];affine(palette.skin[joint]);affine(palette.normal[joint]);const auto p=point(v.position,palette.skin[joint],true),n=point(v.normal,palette.normal[joint],false);normal_scale+=v.weights[slot]*std::sqrt(length_squared(n));for(unsigned axis=0;axis<3;++axis){position[axis]+=v.weights[slot]*p[axis];normal[axis]+=v.weights[slot]*n[axis];}}
 if(length_squared(normal)<=1e-12*normal_scale*normal_scale)normal={v.normal.x,v.normal.y,v.normal.z};position=point(vector(position),world,true);normal=point(vector(normal),normal_matrix(world),false);const auto length=std::sqrt(length_squared(normal));need(std::isfinite(length)&&length>0,"Invalid deformed character normal");for(auto& value:normal)value/=length;return {vector(position),vector(normal)};
}
}
