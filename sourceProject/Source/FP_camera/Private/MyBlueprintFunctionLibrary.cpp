// Fill out your copyright notice in the Description page of Project Settings.


#include "MyBlueprintFunctionLibrary.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Texture2D.h"
#include "Components/Image.h"
#include "Slate/SlateBrushAsset.h"
#include "RenderingThread.h"
#include "Engine/SceneCapture2D.h"
#include "RHICommandList.h"
#include "Engine/World.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Sockets.h"
#include "ImageUtils.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "SocketSubsystem.h"
#include "Kismet/GameplayStatics.h"

// 輸入整數轉換成TArray
TArray<uint8> UMyBlueprintFunctionLibrary::IntToByteArray(int32 Identifier)
{
    // **存入識別碼（小端序）**
    TArray<uint8> ByteArray;
    ByteArray.SetNumUninitialized(4); // int32 佔 4 Bytes

    FMemory::Memcpy(ByteArray.GetData(), &Identifier, sizeof(int32));

    return ByteArray;
}

// **使用 Render Target 獲取視口的寬度和高度**
TArray<uint8> UMyBlueprintFunctionLibrary::CaptureViewportSize(APlayerController* PlayerController, UTextureRenderTarget2D* RenderTarget)
{
    if (!PlayerController || !RenderTarget) return TArray<uint8>();

    int32 Width = RenderTarget->SizeX;
    int32 Height = RenderTarget->SizeY;

    // **存入 Width & Height（小端序）**
    TArray<uint8> SizeData;
    SizeData.SetNumUninitialized(8);
    FMemory::Memcpy(SizeData.GetData(), &Width, sizeof(int32));
    FMemory::Memcpy(SizeData.GetData() + 4, &Height, sizeof(int32));

    return SizeData;
}

// **使用 Render Target 獲取視口的 RGB 數據**
TArray<uint8> UMyBlueprintFunctionLibrary::CaptureViewportRGB(APlayerController* PlayerController, UTextureRenderTarget2D* RenderTarget)
{
    if (!PlayerController || !RenderTarget) return TArray<uint8>();

    // **鎖定 Render Target**
    FTextureRenderTargetResource* RenderTargetResource = RenderTarget->GameThread_GetRenderTargetResource();
    if (!RenderTargetResource)
    {
        UE_LOG(LogTemp, Warning, TEXT("Render Target Resource is null!"));
        return TArray<uint8>();
    }

    // **讀取像素**
    TArray<FColor> PixelData;
    RenderTargetResource->ReadPixels(PixelData);

    if (PixelData.Num() == 0)
    {
        UE_LOG(LogTemp, Warning, TEXT("No pixel data captured from Render Target!"));
        return TArray<uint8>();
    }

    TArray<uint8> RGBData;
    RGBData.SetNumUninitialized(PixelData.Num() * 3);  // 每個像素 3 Bytes (R, G, B)

    uint8* PixelPtr = RGBData.GetData();
    for (const FColor& Color : PixelData)
    {
        *PixelPtr++ = Color.R;
        *PixelPtr++ = Color.G;
        *PixelPtr++ = Color.B;
    }

    return RGBData;
}

FString UMyBlueprintFunctionLibrary::DebugTArrayUint8(const TArray<uint8>& Data)
{
    int32 DataSize = Data.Num();
    FString DebugString = FString::Printf(TEXT("TArray<uint8> Size: %d\n"), DataSize);

    if (DataSize == 0)
    {
        DebugString += TEXT("Data is empty.");
        return DebugString;
    }

    // 只輸出前 50 個字節，避免輸出過多
    int32 MaxBytesToShow = FMath::Min(50, DataSize);
    DebugString += TEXT("Data (Hex): ");

    for (int32 i = 0; i < MaxBytesToShow; i++)
    {
        DebugString += FString::Printf(TEXT("%02X "), Data[i]);
    }

    // 如果資料過大，顯示省略符號
    if (DataSize > MaxBytesToShow)
    {
        DebugString += TEXT("...");
    }

    return DebugString;
}

bool UMyBlueprintFunctionLibrary::UpdateTextureFromByteArray(UTexture2D* Texture, const TArray<uint8>& ByteArray, int32 Width, int32 Height)
{
    if (!Texture)
    {
        UE_LOG(LogTemp, Error, TEXT("Texture is NULL!"));
        return false;
    }

    // **忽略識別碼（跳過前 4 Bytes）**
    const uint8* ImageData = ByteArray.GetData() + 4;
    int32 ImageDataSize = ByteArray.Num() - 4;

    if (ImageDataSize != Width * Height * 3)  // 正確的檢查條件
    {
        UE_LOG(LogTemp, Error, TEXT("ByteArray size mismatch! Expected: %d, Got: %d"), Width * Height * 3, ImageDataSize);
        return false;
    }

    // **初始化 FColor 陣列**
    TArray<FColor> ColorData;
    ColorData.SetNumUninitialized(Width * Height);

    // **轉換 RGB Byte Array 到 FColor**
    for (int i = 0, j = 0; i < ImageDataSize; i += 3, j++)
    {
        uint8 R = ImageData[i];
        uint8 G = ImageData[i + 1];
        uint8 B = ImageData[i + 2];
        uint8 A = 255; // 設定 Alpha = 255 (不透明)

        ColorData[j] = FColor(R, G, B, A);
    }

    // **鎖定 UTexture2D 並寫入數據**
    FTexture2DMipMap& Mip = Texture->GetPlatformData()->Mips[0];
    void* TextureData = Mip.BulkData.Lock(LOCK_READ_WRITE);
    FMemory::Memcpy(TextureData, ColorData.GetData(), Width * Height * sizeof(FColor));
    Mip.BulkData.Unlock();
    Texture->UpdateResource();

    UE_LOG(LogTemp, Log, TEXT("Texture updated successfully!"));
    return true;
}

UTexture2D* UMyBlueprintFunctionLibrary::CreateNewTexture(int32 Width, int32 Height)
{
    // 創建 UTexture2D
    UTexture2D* NewTexture = UTexture2D::CreateTransient(Width, Height);
    if (!NewTexture)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create texture!"));
        return nullptr;
    }

    // 設定貼圖參數
    NewTexture->MipGenSettings = TMGS_NoMipmaps;
    NewTexture->SRGB = false;
    NewTexture->CompressionSettings = TC_Default;
    NewTexture->Filter = TF_Bilinear;
    NewTexture->UpdateResource();

    return NewTexture;
}

bool UMyBlueprintFunctionLibrary::SendDataByUdp(const TArray<uint8>& ImageData, const TArray<uint8>& ImageInfoData, const FString& IP, int32 Port, int32 CharacterId)
{
    if (ImageData.Num() == 0 || ImageInfoData.Num() != 8)
    {
        UE_LOG(LogTemp, Warning, TEXT("Invalid input data."));
        return false;
    }

    // 組合封包資料：CharacterId(4) + ImageInfoData(8) + ImageData(N)
    TArray<uint8> Packet;
    Packet.Reserve(4 + ImageInfoData.Num() + ImageData.Num());

    // 加入 CharacterId
    Packet.Append(reinterpret_cast<uint8*>(&CharacterId), sizeof(int32));

    // 加入 ImageInfoData
    Packet.Append(ImageInfoData);

    // 加入 ImageData
    Packet.Append(ImageData);

    // 建立 socket
    FSocket* UDPSocket = FUdpSocketBuilder(TEXT("UDPSenderSocket"))
        .AsReusable()
        .WithBroadcast()
        .WithSendBufferSize(2 * 1024 * 1024);

    if (!UDPSocket)
    {
        UE_LOG(LogTemp, Error, TEXT("Failed to create UDP socket."));
        return false;
    }

    // 設定目標 IP 與 Port
    FIPv4Address Addr;
    if (!FIPv4Address::Parse(IP, Addr))
    {
        UE_LOG(LogTemp, Error, TEXT("Invalid IP address format: %s"), *IP);
        UDPSocket->Close();
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(UDPSocket);
        return false;
    }

    TSharedRef<FInternetAddr> RemoteAddr = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateInternetAddr();
    RemoteAddr->SetIp(Addr.Value);
    RemoteAddr->SetPort(Port);

    // 傳送封包
    int32 BytesSent = 0;
    bool bSuccess = UDPSocket->SendTo(Packet.GetData(), Packet.Num(), BytesSent, *RemoteAddr);

    if (!bSuccess || BytesSent != Packet.Num())
    {
        UE_LOG(LogTemp, Warning, TEXT("Failed to send all bytes. Sent: %d / %d"), BytesSent, Packet.Num());
    }

    // 清理
    UDPSocket->Close();
    ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(UDPSocket);

    return bSuccess && BytesSent == Packet.Num();
}

TArray<uint8> UMyBlueprintFunctionLibrary::CompressJpegFromRenderTarget(APlayerController* PlayerController, UTextureRenderTarget2D* RenderTarget)
{
    TArray<uint8> CompressedJpeg;

    if (!PlayerController || !RenderTarget)
    {
        UE_LOG(LogTemp, Warning, TEXT("CompressJpegFromRenderTarget: Invalid PlayerController or RenderTarget."));
        return CompressedJpeg;
    }

    FTextureRenderTargetResource* RenderTargetResource = RenderTarget->GameThread_GetRenderTargetResource();
    if (!RenderTargetResource)
    {
        UE_LOG(LogTemp, Warning, TEXT("CompressJpegFromRenderTarget: RenderTargetResource is null."));
        return CompressedJpeg;
    }

    const int32 Width = RenderTarget->SizeX;
    const int32 Height = RenderTarget->SizeY;

    if (Width <= 0 || Height <= 0)
    {
        UE_LOG(LogTemp, Warning, TEXT("CompressJpegFromRenderTarget: Invalid resolution (%d x %d)."), Width, Height);
        return CompressedJpeg;
    }

    TArray<FColor> PixelData;

    // ⭐ 加入這段：色彩校正設定
    FReadSurfaceDataFlags ReadDataFlags(RCM_UNorm);
    ReadDataFlags.SetLinearToGamma(true);  // 🔥 正常色彩輸出關鍵點！

    if (!RenderTargetResource->ReadPixels(PixelData, ReadDataFlags) || PixelData.Num() != Width * Height)
    {
        UE_LOG(LogTemp, Warning, TEXT("CompressJpegFromRenderTarget: Failed to read pixel data or pixel count mismatch."));
        return CompressedJpeg;
    }

    FImageUtils::CompressImageArray(Width, Height, PixelData, CompressedJpeg);

    return CompressedJpeg;
}


TArray<AAWaypointBase*> UMyBlueprintFunctionLibrary::GetAllAvailableWaypoints(UObject* WorldContextObject)
{
    TArray<AActor*> FoundActors;
    UGameplayStatics::GetAllActorsOfClass(WorldContextObject, AAWaypointBase::StaticClass(), FoundActors);

    TArray<AAWaypointBase*> Available;
    for (AActor* Actor : FoundActors)
    {
        AAWaypointBase* Waypoint = Cast<AAWaypointBase>(Actor);
        if (Waypoint && Waypoint->IsAvailable())
        {
            Available.Add(Waypoint);
        }
    }
    return Available;
}

AAWaypointBase* UMyBlueprintFunctionLibrary::GetRandomAvailableWaypoint(UObject* WorldContextObject, AAWaypointBase* Exclude)
{
    TArray<AAWaypointBase*> Available = GetAllAvailableWaypoints(WorldContextObject);

    if (Exclude)
    {
        Available.Remove(Exclude);
    }

    if (Available.Num() == 0)
    {
        return nullptr;
    }

    int32 Index = FMath::RandRange(0, Available.Num() - 1);
    return Available[Index];
}

AAWaypointBase* UMyBlueprintFunctionLibrary::GetNearestAvailableWaypoint(UObject* WorldContextObject, FVector FromLocation)
{
    TArray<AAWaypointBase*> Available = GetAllAvailableWaypoints(WorldContextObject);

    AAWaypointBase* Closest = nullptr;
    float MinDist = TNumericLimits<float>::Max();

    for (AAWaypointBase* WP : Available)
    {
        float Dist = FVector::Dist(FromLocation, WP->GetActorLocation());
        if (Dist < MinDist)
        {
            MinDist = Dist;
            Closest = WP;
        }
    }

    return Closest;
}
USIOJsonObject* UMyBlueprintFunctionLibrary::StringToSIOJsonObject(const FString& JsonString, bool& bSuccess)
{
    TSharedPtr<FJsonObject> ParsedJson;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);

    bSuccess = FJsonSerializer::Deserialize(Reader, ParsedJson) && ParsedJson.IsValid();
    if (!bSuccess)
    {
        return nullptr;
    }

    USIOJsonObject* JsonObject = NewObject<USIOJsonObject>();
    JsonObject->SetRootObject(ParsedJson);
    return JsonObject;
}