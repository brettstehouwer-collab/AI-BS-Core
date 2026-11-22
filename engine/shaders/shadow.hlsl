cbuffer ShadowCamera : register(b0) {row_major float4x4 lightViewProjection;};
float4 vertex_main(float3 position:POSITION):SV_POSITION{return mul(float4(position,1),lightViewProjection);}
