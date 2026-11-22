struct PointLightConstants {float4 positionRadius;float4 colorIntensity;};
cbuffer LightingConstants : register(b2) {
 float4 ambientExposure;
 float4 directionIntensity;
 float4 directionalColor;
 uint4 lightControls;
 row_major float4x4 shadowViewProjection;
 float4 shadowParameters;
 PointLightConstants pointLights[32];
};
Texture2D<float> directionalShadowMap : register(t1);
SamplerComparisonState shadowSampler : register(s1);
float authored_transfer(float x){return x<=0.0031308?12.92*x:1.055*pow(max(x,0),1.0/2.4)-0.055;}
float directional_visibility(float3 world){
 [branch] if(lightControls.z==0)return 1;
 const float4 projected=mul(float4(world,1),shadowViewProjection);
 const float3 p=projected.xyz/projected.w;
 const float2 uv=float2(p.x*.5+.5,.5-p.y*.5);
 if(any(uv<=0)||any(uv>=1)||p.z<0||p.z>1)return 1;
 return directionalShadowMap.SampleCmpLevelZero(shadowSampler,uv,p.z-shadowParameters.x);
}
float3 authored_lighting(float3 world,float3 normal,float3 base,float emission){
 const float3 n=normalize(normal);
 float3 irradiance=ambientExposure.rgb;
 const float3 direction=directionIntensity.xyz*rsqrt(max(dot(directionIntensity.xyz,directionIntensity.xyz),1e-20));
 irradiance+=directionalColor.rgb*directionIntensity.w*max(dot(n,-direction),0)*directional_visibility(world);
 [loop]for(uint i=0;i<lightControls.y;++i){
  const float3 delta=pointLights[i].positionRadius.xyz-world;const float distance=length(delta);
  const float3 L=distance<=1e-6?n:delta/distance;
  const float falloff=saturate(1-distance/pointLights[i].positionRadius.w);
  irradiance+=pointLights[i].colorIntensity.rgb*pointLights[i].colorIntensity.w*max(dot(n,L),0)*falloff*falloff;
 }
 const float3 radiance=base*irradiance+base*max(emission,0);
 const float3 mapped=1-exp(-max(radiance,0)*ambientExposure.w);
 return float3(authored_transfer(mapped.r),authored_transfer(mapped.g),authored_transfer(mapped.b));
}
