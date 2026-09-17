// Fill out your copyright notice in the Description page of Project Settings.


#include "AWaypointBase.h"

// Sets default values
AAWaypointBase::AAWaypointBase()
{
 	// Set this actor to call Tick() every frame.  You can turn this off to improve performance if you don't need it.
	PrimaryActorTick.bCanEverTick = false;

}
bool AAWaypointBase::IsAvailable() const
{
    return OccupiedBy == nullptr;
}

void AAWaypointBase::Reserve(AActor* Who)
{
    OccupiedBy = Who;
}

void AAWaypointBase::Release()
{
    OccupiedBy = nullptr;
}
// Called when the game starts or when spawned
//void AAWaypointBase::BeginPlay()
//{
//	Super::BeginPlay();
//	
//}
//
//// Called every frame
//void AAWaypointBase::Tick(float DeltaTime)
//{
//	Super::Tick(DeltaTime);
//
//}

