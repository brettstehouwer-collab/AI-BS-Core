cbuffer CameraConstants : register(b0) { row_major float4x4 viewProjection; };
cbuffer CharacterConstants : register(b1) {
 row_major float4x4 skin[64];
 row_major float4x4 skinNormal[64];
 row_major float4x4 characterWorld;
 row_major float4x4 characterWorldNormal;
 float4 tintEmission;
 float opacity;uint jointCount;uint2 reserved;
 float4 cameraWorld;
};
cbuffer MaterialConstants : register(b3) { float4 materialColorEmission;uint materialOptions;float materialRoughness; };
Texture2D<float4> characterAlbedo : register(t0);
SamplerState characterSampler : register(s0);
#include "lighting.hlsli"
struct VertexInput {
 float3 position:POSITION;float3 normal:NORMAL;float3 color:COLOR;
 float emission:TEXCOORD0;float2 uv:TEXCOORD1;
 uint4 joints:BLENDINDICES;float4 weights:BLENDWEIGHT;
};
struct PixelInput {
 float4 position:SV_POSITION;float3 world:TEXCOORD0;float3 normal:NORMAL;
 float3 color:COLOR;float emission:TEXCOORD1;float2 uv:TEXCOORD2;
};
float safe_length(float3 v) {
 const float scale=max(max(abs(v.x),abs(v.y)),abs(v.z));
 return scale>0?scale*length(v/scale):0;
}
float3 safe_unit(float3 v) {
 const float scale=max(max(abs(v.x),abs(v.y)),abs(v.z));
 return scale>0?normalize(v/scale):float3(0,1,0);
}
PixelInput vertex_main(VertexInput input) {
 float3 position=0,normal=0;float normalScale=0;
 [unroll]for(uint slot=0;slot<4;++slot) {
  const float weight=input.weights[slot];
  const uint joint=input.joints[slot];
  const float3 transformedNormal=mul(float4(input.normal,0),skinNormal[joint]).xyz;
  position+=weight*mul(float4(input.position,1),skin[joint]).xyz;
  normal+=weight*transformedNormal;
  normalScale+=weight*safe_length(transformedNormal);
 }
 // Position is a weighted XYZ value, then a point with W=1. Carrying a
 // near-one weight sum into W would incorrectly scale world translation.
 if(safe_length(normal)<=1e-6*normalScale)normal=input.normal;
 PixelInput output;
 output.world=mul(float4(position,1),characterWorld).xyz;
 output.position=mul(float4(output.world,1),viewProjection);
 output.normal=safe_unit(mul(float4(normal,0),characterWorldNormal).xyz);
 output.color=input.color*tintEmission.rgb;output.emission=input.emission+tintEmission.a;
 output.uv=input.uv;
 return output;
}
float inverse_transfer(float x) {return x<=.04045?x/12.92:pow((max(x,0)+.055)/1.055,2.4);}
// Dielectric direct response in the engine's diffuse-normalized light units.
// Ambient remains diffuse; this does not claim IBL or subsurface skin transport.
float3 surface_response(float3 n,float3 v,float3 l,float3 base,float roughness) {
 const float nl=saturate(dot(n,l)),nv=max(saturate(dot(n,v)),1e-5);
 if(nl<=0)return 0;
 const float3 h=safe_unit(v+l);
 const float nh=saturate(dot(n,h)),vh=saturate(dot(v,h));
 const float a=roughness*roughness,a2=a*a;
 const float denominator=nh*nh*(a2-1)+1;
 const float distribution=a2/(3.14159265359*max(denominator*denominator,1e-12));
 const float k=(roughness+1)*(roughness+1)/8;
 const float geometry=(nv/(nv*(1-k)+k))*(nl/(nl*(1-k)+k));
 const float fresnel=.04+.96*pow(1-vh,5);
 const float specular=3.14159265359*distribution*geometry*fresnel/max(4*nv*nl,1e-6);
 return (base*(1-fresnel)+specular)*nl;
}
float3 surface_lighting(float3 world,float3 normal,float3 base,float emission,float roughness) {
 const float3 n=safe_unit(normal),v=safe_unit(cameraWorld.xyz-world);
 float3 radiance=base*ambientExposure.rgb;
 const float3 direction=safe_unit(directionIntensity.xyz);
 radiance+=surface_response(n,v,-direction,base,roughness)*directionalColor.rgb*directionIntensity.w*directional_visibility(world);
 [loop]for(uint i=0;i<lightControls.y;++i) {
  const float3 delta=pointLights[i].positionRadius.xyz-world;const float distance=length(delta);
  const float3 l=distance<=1e-6?n:delta/distance;
  const float falloff=saturate(1-distance/pointLights[i].positionRadius.w);
  radiance+=surface_response(n,v,l,base,roughness)*pointLights[i].colorIntensity.rgb*pointLights[i].colorIntensity.w*falloff*falloff;
 }
 const float3 mapped=1-exp(-max(radiance+base*max(emission,0),0)*ambientExposure.w);
 return float3(authored_transfer(mapped.r),authored_transfer(mapped.g),authored_transfer(mapped.b));
}
float4 pixel_main(PixelInput input,bool front:SV_IsFrontFace):SV_TARGET {
 const float3 base=input.color*materialColorEmission.rgb*characterAlbedo.Sample(characterSampler,input.uv).rgb;
 const float emission=input.emission+materialColorEmission.a;
 float3 normal=safe_unit(input.normal);
 if((materialOptions&1)!=0&&!front)normal=-normal;
 float3 encoded;
 [branch]if(lightControls.x!=0) {
  [branch]if(materialRoughness<1)encoded=surface_lighting(input.world,normal,base,emission,materialRoughness);
  else encoded=authored_lighting(input.world,normal,base,emission);
 }
 else {
  const float diffuse=max(dot(normal,normalize(float3(-.35,.85,-.4))),0);
  [branch]if(materialRoughness<1) {
   const float3 view=safe_unit(cameraWorld.xyz-input.world);
   encoded=lerp(base*.28+.72*surface_response(normal,view,normalize(float3(-.35,.85,-.4)),base,materialRoughness),base,saturate(emission));
  }else encoded=lerp(base*(.28+diffuse*.72),base,saturate(emission));
  if((materialOptions&2)!=0)encoded=float3(authored_transfer(encoded.r),authored_transfer(encoded.g),authored_transfer(encoded.b));
 }
 // Existing scenery writes encoded presentation values to its UNORM view.
 // This pass uses the sRGB view of that same target, so decode the shader's
 // encoded lighting result before hardware linear-alpha composition.
 return float4(inverse_transfer(encoded.r),inverse_transfer(encoded.g),inverse_transfer(encoded.b),opacity);
}
