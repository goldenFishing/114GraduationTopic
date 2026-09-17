// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Texture2D.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Networking.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Components/Image.h"
#include "SIOJsonObject.h"
#include "AWaypointBase.h"
#include "Slate/SlateBrushAsset.h"
#include "Engine/World.h"
#include "MyBlueprintFunctionLibrary.generated.h"

UCLASS()
class FP_CAMERA_API UMyBlueprintFunctionLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
	
public:

	UFUNCTION(BlueprintCallable, Category = "Customize|Viewport")
	static TArray<uint8> CaptureViewportRGB(APlayerController* PlayerController, UTextureRenderTarget2D* RenderTarget);

	UFUNCTION(BlueprintCallable, Category = "Customize|Viewport")
	static TArray<uint8> CaptureViewportSize(APlayerController* PlayerController, UTextureRenderTarget2D* RenderTarget);

	UFUNCTION(BlueprintCallable, Category = "Customize|Debug")
	static FString DebugTArrayUint8(const TArray<uint8>& Data);

	UFUNCTION(BlueprintCallable, Category = "Customize|Texture")
	static bool UpdateTextureFromByteArray(UTexture2D* Texture, const TArray<uint8>& ByteArray, int32 Width, int32 Height);

	UFUNCTION(BlueprintCallable, Category = "Customize|Texture")
	static UTexture2D* CreateNewTexture(int32 Width, int32 Height);

	UFUNCTION(BlueprintCallable, Category = "Customize|Transformation", meta = (ToolTip = "轉TArray<uint8>"))
	static TArray<uint8> IntToByteArray(int32 Identifier);

	UFUNCTION(BlueprintCallable, Category = "Customize|Send to UDP")
	static bool SendDataByUdp(const TArray<uint8>& ImageData, const TArray<uint8>& ImageInfoData, const FString& IP, int32 Port, int32 CharacterId);

	UFUNCTION(BlueprintCallable, Category = "Customize|Transformation", meta = (ToolTip = "把RT的Fcolor壓成JPG的TArray<uint8>"))
	static TArray<uint8> CompressJpegFromRenderTarget(APlayerController* PlayerController, UTextureRenderTarget2D* RenderTarget);

	// 取得所有場上可用的 Waypoint
	UFUNCTION(BlueprintCallable, Category = "Customize|Waypoint")
	static TArray<AAWaypointBase*> GetAllAvailableWaypoints(UObject* WorldContextObject);

	// 隨機選擇一個可用的點（可選排除某個）
	UFUNCTION(BlueprintCallable, Category = "Customize|Waypoint")
	static AAWaypointBase* GetRandomAvailableWaypoint(UObject* WorldContextObject, AAWaypointBase* Exclude = nullptr);

	// 找最近的可用點
	UFUNCTION(BlueprintCallable, Category = "Customize|Waypoint")
	static AAWaypointBase* GetNearestAvailableWaypoint(UObject* WorldContextObject, FVector FromLocation);

	UFUNCTION(BlueprintCallable, Category = "SIOJson")
	static USIOJsonObject* StringToSIOJsonObject(const FString& JsonString, bool& bSuccess);

};
