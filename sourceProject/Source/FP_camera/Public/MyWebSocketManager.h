#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "IWebSocket.h"
#include "WebSocketsModule.h"
#include "MyWebSocketManager.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnWebSocketMessageReceived, const FString&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FWebSocketConnectedSignature);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FWebSocketErrorSignature, const FString&, Error);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FWebSocketClosedSignature, int32, StatusCode, const FString&, Reason, bool, bWasClean);

UCLASS()
class FP_CAMERA_API AMyWebSocketManager : public AActor
{
    GENERATED_BODY()

public:
    AMyWebSocketManager();

    UPROPERTY(BlueprintAssignable, Category = "WebSocket")
    FOnWebSocketMessageReceived OnMessageReceived;


    UFUNCTION(BlueprintCallable, Category = "WebSocket")
    void SendMessageToServer(const FString& Message);

    UPROPERTY(BlueprintAssignable, Category = "WebSocket")
    FWebSocketConnectedSignature OnConnected;

    UPROPERTY(BlueprintAssignable, Category = "WebSocket")
    FWebSocketErrorSignature OnConnectionError;

    UPROPERTY(BlueprintAssignable, Category = "WebSocket")
    FWebSocketClosedSignature OnClosed;

    UFUNCTION(BlueprintPure, Category = "WebSocket")
    bool IsSocketConnected() const { return Socket.IsValid() && Socket->IsConnected(); }

    UFUNCTION(BlueprintCallable, Category = "WebSocket")
    void ConnectWebSocket();

    void CleanupSocket();

protected:
    /*virtual void BeginPlay() override;*/
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    TSharedPtr<IWebSocket> Socket;

    void HandleMessage(const FString& Message);
};
