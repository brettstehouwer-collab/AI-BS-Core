cbuffer CameraConstants : register(b0) { row_major float4x4 viewProjection; };
#include "lighting.hlsli"
struct VertexInput { float3 position : POSITION; float3 normal : NORMAL; float3 color : COLOR; float emission : TEXCOORD0; };
struct PixelInput { float4 position : SV_POSITION; float3 normal : NORMAL; float3 color : COLOR; float emission : TEXCOORD0;float3 world:TEXCOORD1; };
PixelInput vertex_main(VertexInput input) {
 PixelInput output;
 output.position = mul(float4(input.position, 1), viewProjection);
 output.normal = input.normal; output.color = input.color; output.emission = input.emission;
 output.world=input.position;
 return output;
}
float4 pixel_main(PixelInput input) : SV_TARGET {
 [branch] if(lightControls.x!=0)return float4(authored_lighting(input.world,input.normal,input.color,input.emission),1);
 float diffuse = max(dot(normalize(input.normal), normalize(float3(-0.35, 0.85, -0.4))), 0);
 float3 lit = input.color * (0.28 + diffuse * 0.72);
 return float4(lerp(lit, input.color, input.emission), 1);
}
