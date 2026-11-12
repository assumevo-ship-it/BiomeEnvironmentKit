#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "BiomeWindSource.generated.h"

UINTERFACE(BlueprintType, MinimalAPI)
class UBiomeWindSource : public UInterface
{
	GENERATED_BODY()
};

/**
 * Anything that knows the wind (a sky or weather actor, a game state, a Blueprint) can drive ABiomeOcean by implementing
 * this interface; the ocean has no dependency on who implements it. Implement it in C++ (override
 * GetBiomeWindVelocity_Implementation) or in a Blueprint (Class Settings > Interfaces).
 */
class BIOMEOCEAN_API IBiomeWindSource
{
	GENERATED_BODY()
public:
	/** The wind 10 m above the sea, in metres per second: the horizontal direction the air moves towards times its speed.
	 *  Z is ignored. */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Biome|Wind")
	FVector GetBiomeWindVelocity() const;
};
