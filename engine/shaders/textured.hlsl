cbuffer CameraConstants : register(b0) { row_major float4x4 viewProjection; };
#include "lighting.hlsli"
cbuffer MaterialConstants : register(b1) {float3 tint;float emission;};
Texture2D albedo : register(t0);
SamplerState surfaceSampler : register(s0);
struct VertexInput {float3 position:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;};
struct PixelInput {float4 position:SV_POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;float3 world:TEXCOORD1;};
PixelInput vertex_main(VertexInput input){PixelInput o;o.position=mul(float4(input.position,1),viewProjection);o.normal=input.normal;o.uv=input.uv;o.world=input.position;return o;}
float transfer(float x){return x<=0.0031308?12.92*x:1.055*pow(max(x,0),1.0/2.4)-0.055;}
float4 pixel_main(PixelInput input):SV_TARGET{
 float3 base=albedo.Sample(surfaceSampler,input.uv).rgb*tint;
 [branch] if(lightControls.x!=0)return float4(authored_lighting(input.world,input.normal,base,emission),1);
 float diffuse=max(dot(normalize(input.normal),normalize(float3(-0.35,0.85,-0.4))),0);
 float3 lit=lerp(base*(0.28+0.72*diffuse),base,emission);
 return float4(transfer(lit.r),transfer(lit.g),transfer(lit.b),1);
}
