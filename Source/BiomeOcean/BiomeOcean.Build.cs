using UnrealBuildTool;

public class BiomeOcean : ModuleRules
{
	public BiomeOcean(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "RenderCore", "RHI", "MeshDescription", "StaticMeshDescription" });
	}
}
