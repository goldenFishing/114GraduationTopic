#include "MyWebSocketManager.h"
// 如果尚未包含，建議加入此標頭以支援 TWeakObjectPtr
#include "UObject/WeakObjectPtrTemplates.h" 

AMyWebSocketManager::AMyWebSocketManager()
{
    PrimaryActorTick.bCanEverTick = false;
}

void AMyWebSocketManager::CleanupSocket()
{
    if (Socket.IsValid())
    {
        // 如果連線尚未關閉，強制關閉
        if (Socket->IsConnected())
        {
            Socket->Close();
        }

        // 移除所有已綁定的 Lambda 事件，避免記憶體存取違規或重複觸發
        Socket->OnConnected().Clear();
        Socket->OnConnectionError().Clear();
        Socket->OnClosed().Clear();
        Socket->OnMessage().Clear();

        // 釋放智慧指標
        Socket.Reset();
        Socket = nullptr;
    }
}

// 覆寫 EndPlay 以確保 Actor 銷毀時正確釋放網路資源
void AMyWebSocketManager::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // 直接複用清理邏輯，確保委派解綁與智慧指標重置
    CleanupSocket();
    UE_LOG(LogTemp, Log, TEXT("[WebSocket] Socket cleaned up due to Actor EndPlay."));

    Super::EndPlay(EndPlayReason);
}

void AMyWebSocketManager::ConnectWebSocket()
{
    // 如果已經連線中，就不重複執行
    if (IsSocketConnected()) return;

    CleanupSocket();
    
    if (!FModuleManager::Get().IsModuleLoaded("WebSockets"))
    {
        FModuleManager::LoadModuleChecked<FWebSocketsModule>("WebSockets");
    }

    Socket = FWebSocketsModule::Get().CreateWebSocket(TEXT("ws://127.0.0.1:8765"));

    // 建立弱參照指標，防止 Lambda 執行時 Actor 已被銷毀
    TWeakObjectPtr<AMyWebSocketManager> WeakThis(this);

    Socket->OnConnected().AddLambda([WeakThis]()
        {
            if (WeakThis.IsValid())
            {
                WeakThis->OnConnected.Broadcast();
                UE_LOG(LogTemp, Log, TEXT("[WebSocket] Connected successfully."));
            }
        });

    Socket->OnConnectionError().AddLambda([WeakThis](const FString& Error)
        {
            if (WeakThis.IsValid())
            {
                WeakThis->OnConnectionError.Broadcast(Error);
                UE_LOG(LogTemp, Error, TEXT("[WebSocket] Connection Error: %s"), *Error);
            }
        });

    Socket->OnClosed().AddLambda([WeakThis](int32 StatusCode, const FString& Reason, bool bWasClean)
        {
            if (WeakThis.IsValid())
            {
                WeakThis->OnClosed.Broadcast(StatusCode, Reason, bWasClean);
                UE_LOG(LogTemp, Warning, TEXT("[WebSocket] Closed. Status: %d, Reason: %s"), StatusCode, *Reason);
            }
        });

    // AddUObject 內部具備 UObject 生命週期檢查，因此安全
    Socket->OnMessage().AddUObject(this, &AMyWebSocketManager::HandleMessage);

    Socket->Connect();
}

// 合併後的 HandleMessage 實作
void AMyWebSocketManager::HandleMessage(const FString& Message)
{
    UE_LOG(LogTemp, Warning, TEXT("[WebSocket] Message Received: %s"), *Message);
    OnMessageReceived.Broadcast(Message);
}

// 合併後的 SendMessageToServer 實作
void AMyWebSocketManager::SendMessageToServer(const FString& Message)
{
    if (Socket.IsValid() && Socket->IsConnected())
    {
        Socket->Send(Message);
        UE_LOG(LogTemp, Log, TEXT("[WebSocket] Sent to server: %s"), *Message);
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("[WebSocket] Send failed: socket not connected or invalid."));
    }
}