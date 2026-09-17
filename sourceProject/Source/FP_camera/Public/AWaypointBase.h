// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AWaypointBase.generated.h"

UCLASS()
class FP_CAMERA_API AAWaypointBase : public AActor
{
	GENERATED_BODY()
	
public:	
	// Sets default values for this actor's properties
	AAWaypointBase();
    // 可用於識別點編號 / 類型

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Waypoint")
    FName PointID;

    // 進場者紀錄（簡化範例）
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Waypoint")
    AActor* OccupiedBy;

    // 半徑用於抵達判定
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Waypoint")
    float AcceptanceRadius = 100.0f;

    // 判斷是否可用
    UFUNCTION(BlueprintCallable, Category = "Waypoint")
    bool IsAvailable() const;

    // 外部呼叫：標記佔用
    UFUNCTION(BlueprintCallable, Category = "Waypoint")
    void Reserve(AActor* Who);

    // 外部呼叫：釋放點位
    UFUNCTION(BlueprintCallable, Category = "Waypoint")
    void Release();

//protected:
//	// Called when the game starts or when spawned
//	virtual void BeginPlay() override;
//
//public:	
//	// Called every frame
//	virtual void Tick(float DeltaTime) override;


};
