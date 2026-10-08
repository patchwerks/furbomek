-- Rebinds ten included characters to a newly imported combined-FBX bundle.
-- Generated from roblox_import/import_manifest.json. All validation happens before mutation.

local HttpService = game:GetService("HttpService")
local ServerStorage = game:GetService("ServerStorage")
local ChangeHistoryService = game:GetService("ChangeHistoryService")
local Selection = game:GetService("Selection")

local ASSETS = HttpService:JSONDecode([==[[{"name":"Swarm_02_FurScout","height":7,"position":[24,0,31],"parts":[{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_machined_edges_a9413_01","material":"02 Fur Needle Scout machined edges"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_recesses_62fd4_01","material":"02 Fur Needle Scout recesses"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_warm_painted_al_b8c29_01","material":"02 Fur Needle Scout warm painted alloy"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_soft_fur_04482_01","material":"02 Fur Needle Scout soft fur"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_ivory_eye_mask_5cd4d_01","material":"02 Fur Needle Scout ivory eye mask"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_dark_steel_3b4b1_01","material":"02 Fur Needle Scout dark steel"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_smoky_iris_050ff_01","material":"02 Fur Needle Scout smoky iris"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_split_beak_c430e_01","material":"02 Fur Needle Scout split beak"},{"name":"Swarm_02_FurScout__02_Fur_Needle_Scout_ear_velvet_18b11_01","material":"02 Fur Needle Scout ear velvet"}],"materials":{"02 Fur Needle Scout recesses":{"rgb":[33,38,41]},"02 Fur Needle Scout warm painted alloy":{"rgb":[175,177,170]},"02 Fur Needle Scout machined edges":{"rgb":[208,211,205]},"02 Fur Needle Scout soft fur":{"rgb":[239,239,232]},"02 Fur Needle Scout ivory eye mask":{"rgb":[243,242,229]},"02 Fur Needle Scout dark steel":{"rgb":[101,108,108]},"02 Fur Needle Scout smoky iris":{"rgb":[132,153,142]},"02 Fur Needle Scout split beak":{"rgb":[243,200,44]},"02 Fur Needle Scout ear velvet":{"rgb":[89,97,97]}}},{"name":"Furbomek_Boss_F069","height":18,"position":[0,0,16],"parts":[{"name":"Furbomek_Boss_F069__Jet_black_plush_e66bd_01","material":"Jet black plush"},{"name":"Furbomek_Boss_F069__Jet_black_plush_e66bd_02","material":"Jet black plush"},{"name":"Furbomek_Boss_F069__Jet_black_plush_e66bd_03","material":"Jet black plush"},{"name":"Furbomek_Boss_F069__Jet_black_plush_e66bd_04","material":"Jet black plush"},{"name":"Furbomek_Boss_F069__Moulded_black_ABS_ed14b_01","material":"Moulded black ABS"},{"name":"Furbomek_Boss_F069__Moulded_black_ABS_ed14b_02","material":"Moulded black ABS"},{"name":"Furbomek_Boss_F069__Moulded_black_ABS_ed14b_03","material":"Moulded black ABS"},{"name":"Furbomek_Boss_F069__Charcoal_body_casing_3d382_01","material":"Charcoal body casing"},{"name":"Furbomek_Boss_F069__Charcoal_body_casing_3d382_02","material":"Charcoal body casing"},{"name":"Furbomek_Boss_F069__Amber_iris_fibres_2b0b3_01","material":"Amber iris fibres"},{"name":"Furbomek_Boss_F069__Amber_iris_fibres_2b0b3_02","material":"Amber iris fibres"},{"name":"Furbomek_Boss_F069__v7_satin_black_bracket_metal_0da40_01","material":"v7 satin black bracket metal"},{"name":"Furbomek_Boss_F069__v7_recessed_screw_sockets_35e0e_01","material":"v7 recessed screw sockets"},{"name":"Furbomek_Boss_F069__Orange_servo_lead_1c368_01","material":"Orange servo lead"},{"name":"Furbomek_Boss_F069__Orange_servo_lead_1c368_02","material":"Orange servo lead"},{"name":"Furbomek_Boss_F069__Bracket_hardware_5e3f6_01","material":"Bracket hardware"},{"name":"Furbomek_Boss_F069__Bracket_hardware_5e3f6_02","material":"Bracket hardware"},{"name":"Furbomek_Boss_F069__Bracket_hardware_5e3f6_03","material":"Bracket hardware"},{"name":"Furbomek_Boss_F069__Bracket_hardware_5e3f6_04","material":"Bracket hardware"},{"name":"Furbomek_Boss_F069__Bracket_hardware_5e3f6_05","material":"Bracket hardware"},{"name":"Furbomek_Boss_F069__Plain_metal_battery_sleeves_fa103_01","material":"Plain metal battery sleeves"},{"name":"Furbomek_Boss_F069__Chestnut_iris_3d21b_01","material":"Chestnut iris"},{"name":"Furbomek_Boss_F069__Controller_green_board_a6ab8_01","material":"Controller green board"},{"name":"Furbomek_Boss_F069__Black_controller_PCB_f2a81_01","material":"Black controller PCB"},{"name":"Furbomek_Boss_F069__White_eye_plastic_bf441_01","material":"White eye plastic"},{"name":"Furbomek_Boss_F069__Red_supply_lead_f4a20_01","material":"Red supply lead"},{"name":"Furbomek_Boss_F069__Dark_iris_fibres_aedf3_01","material":"Dark iris fibres"},{"name":"Furbomek_Boss_F069__Soft_charcoal_fibres_0be06_01","material":"Soft charcoal fibres"},{"name":"Furbomek_Boss_F069__Deep_black_fibres_8a4d1_01","material":"Deep black fibres"},{"name":"Furbomek_Boss_F069__Battery_bay_black_plastic_b3b13_01","material":"Battery bay black plastic"},{"name":"Furbomek_Boss_F069__Yellow_beak_aed9d_01","material":"Yellow beak"},{"name":"Furbomek_Boss_F069__Deep_mouth_cavity_e7eda_01","material":"Deep mouth cavity"},{"name":"Furbomek_Boss_F069__Recessed_red_mouth_1062f_01","material":"Recessed red mouth"},{"name":"Furbomek_Boss_F069__Glossy_black_pupil_5cde1_01","material":"Glossy black pupil"},{"name":"Furbomek_Boss_F069__Fine_dark_crown_fibres_5ed8b_01","material":"Fine dark crown fibres"},{"name":"Furbomek_Boss_F069__Fine_black_eyelashes_0b80a_01","material":"Fine black eyelashes"},{"name":"Furbomek_Boss_F069__Foot_elastomer_21412_01","material":"Foot elastomer"}],"materials":{"Bracket hardware":{"rgb":[175,181,182]},"Plain metal battery sleeves":{"rgb":[93,101,105]},"Moulded black ABS":{"rgb":[36,40,41]},"Jet black plush":{"rgb":[18,20,22]},"Chestnut iris":{"rgb":[115,74,43]},"Controller green board":{"rgb":[39,82,60]},"Black controller PCB":{"rgb":[34,44,43]},"White eye plastic":{"rgb":[236,237,229]},"Orange servo lead":{"rgb":[197,124,58]},"Red supply lead":{"rgb":[153,31,33]},"Dark iris fibres":{"rgb":[58,34,22]},"Soft charcoal fibres":{"rgb":[29,31,34]},"Deep black fibres":{"rgb":[10,13,16]},"Battery bay black plastic":{"rgb":[33,36,36]},"Yellow beak":{"rgb":[249,215,22]},"Deep mouth cavity":{"rgb":[16,7,3]},"Charcoal body casing":{"rgb":[61,68,68]},"Amber iris fibres":{"rgb":[124,82,45]},"Recessed red mouth":{"rgb":[129,22,16]},"Glossy black pupil":{"rgb":[7,10,10]},"Fine dark crown fibres":{"rgb":[24,25,24]},"Fine black eyelashes":{"rgb":[24,22,18]},"v7 satin black bracket metal":{"rgb":[36,41,42]},"v7 recessed screw sockets":{"rgb":[10,13,13]},"Foot elastomer":{"rgb":[22,29,29]}}},{"name":"Swarm_01_ArmoredSmile","height":7,"position":[-25,0,25],"parts":[{"name":"Swarm_01_ArmoredSmile__01_Armored_Smile_Hexapod_machined_e_42a56_01","material":"01 Armored Smile Hexapod machined edges"},{"name":"Swarm_01_ArmoredSmile__01_Armored_Smile_Hexapod_machined_e_42a56_02","material":"01 Armored Smile Hexapod machined edges"},{"name":"Swarm_01_ArmoredSmile__01_Armored_Smile_Hexapod_recesses_e6457_01","material":"01 Armored Smile Hexapod recesses"},{"name":"Swarm_01_ArmoredSmile__01_Armored_Smile_Hexapod_pale_warm__18a35_01","material":"01 Armored Smile Hexapod pale warm enamel"},{"name":"Swarm_01_ArmoredSmile__01_Armored_Smile_Hexapod_dark_steel_0daca_01","material":"01 Armored Smile Hexapod dark steel"},{"name":"Swarm_01_ArmoredSmile__01_Armored_Smile_Hexapod_cast_porce_f5958_01","material":"01 Armored Smile Hexapod cast porcelain mask"}],"materials":{"01 Armored Smile Hexapod recesses":{"rgb":[33,38,41]},"01 Armored Smile Hexapod pale warm enamel":{"rgb":[199,197,184]},"01 Armored Smile Hexapod machined edges":{"rgb":[208,211,205]},"01 Armored Smile Hexapod dark steel":{"rgb":[101,108,108]},"01 Armored Smile Hexapod cast porcelain mask":{"rgb":[226,225,211]}}},{"name":"Swarm_03_SkullSentinel","height":7,"position":[-34,0,-1],"parts":[{"name":"Swarm_03_SkullSentinel__03_Skull_Sentinel_machined_edges_bb09a_01","material":"03 Skull Sentinel machined edges"},{"name":"Swarm_03_SkullSentinel__03_Skull_Sentinel_machined_edges_bb09a_02","material":"03 Skull Sentinel machined edges"},{"name":"Swarm_03_SkullSentinel__03_Skull_Sentinel_recesses_c6f05_01","material":"03 Skull Sentinel recesses"},{"name":"Swarm_03_SkullSentinel__03_Skull_Sentinel_warm_painted_allo_fa400_01","material":"03 Skull Sentinel warm painted alloy"},{"name":"Swarm_03_SkullSentinel__03_Skull_Sentinel_dark_steel_f2b1c_01","material":"03 Skull Sentinel dark steel"},{"name":"Swarm_03_SkullSentinel__03_Skull_Sentinel_cast_porcelain_ma_76037_01","material":"03 Skull Sentinel cast porcelain mask"}],"materials":{"03 Skull Sentinel recesses":{"rgb":[33,38,41]},"03 Skull Sentinel warm painted alloy":{"rgb":[175,177,170]},"03 Skull Sentinel machined edges":{"rgb":[208,211,205]},"03 Skull Sentinel dark steel":{"rgb":[101,108,108]},"03 Skull Sentinel cast porcelain mask":{"rgb":[226,225,211]}}},{"name":"Swarm_04_CannonWalker","height":7,"position":[34,0,2],"parts":[{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_machined_edges_09881_01","material":"04 Cannon Quadruped machined edges"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_machined_edges_09881_02","material":"04 Cannon Quadruped machined edges"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_warm_painted_al_b8795_01","material":"04 Cannon Quadruped warm painted alloy"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_dark_steel_39a2e_01","material":"04 Cannon Quadruped dark steel"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_recesses_f091e_01","material":"04 Cannon Quadruped recesses"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_soft_fur_f5c49_01","material":"04 Cannon Quadruped soft fur"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_ivory_eye_mask_99d98_01","material":"04 Cannon Quadruped ivory eye mask"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_smoky_iris_4592e_01","material":"04 Cannon Quadruped smoky iris"},{"name":"Swarm_04_CannonWalker__04_Cannon_Quadruped_split_beak_32be1_01","material":"04 Cannon Quadruped split beak"}],"materials":{"04 Cannon Quadruped warm painted alloy":{"rgb":[175,177,170]},"04 Cannon Quadruped dark steel":{"rgb":[101,108,108]},"04 Cannon Quadruped recesses":{"rgb":[33,38,41]},"04 Cannon Quadruped machined edges":{"rgb":[208,211,205]},"04 Cannon Quadruped soft fur":{"rgb":[239,237,230]},"04 Cannon Quadruped ivory eye mask":{"rgb":[243,242,229]},"04 Cannon Quadruped smoky iris":{"rgb":[132,153,142]},"04 Cannon Quadruped split beak":{"rgb":[243,200,44]}}},{"name":"Cudgel_Tank_01","height":6,"position":[-13,0,-17],"parts":[{"name":"Cudgel_Tank_01__05_tracked_graft_tank_satin_pale_al_c7692_01","material":"05_tracked_graft_tank satin pale alloy"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_recessed_gunm_b141d_01","material":"05_tracked_graft_tank recessed gunmetal"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_machined_edge_886a1_01","material":"05_tracked_graft_tank machined edges"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_recesses_b2248_01","material":"05_tracked_graft_tank recesses"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_warm_painted__7d01c_01","material":"05_tracked_graft_tank warm painted alloy"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_soft_fur_4d2c6_01","material":"05_tracked_graft_tank soft fur"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_ivory_eye_mas_7733c_01","material":"05_tracked_graft_tank ivory eye mask"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_machined_edge_92737_01","material":"05_tracked_graft_tank machined edge"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_smoky_iris_a0908_01","material":"05_tracked_graft_tank smoky iris"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_dark_steel_1d1ab_01","material":"05_tracked_graft_tank dark steel"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_split_beak_22b10_01","material":"05_tracked_graft_tank split beak"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_ear_velvet_15cf5_01","material":"05_tracked_graft_tank ear velvet"},{"name":"Cudgel_Tank_01__05_tracked_graft_tank_track_rubber_0a761_01","material":"05_tracked_graft_tank track rubber"}],"materials":{"05_tracked_graft_tank satin pale alloy":{"rgb":[184,189,189]},"05_tracked_graft_tank machined edges":{"rgb":[208,211,205]},"05_tracked_graft_tank recesses":{"rgb":[33,38,41]},"05_tracked_graft_tank warm painted alloy":{"rgb":[175,177,170]},"05_tracked_graft_tank recessed gunmetal":{"rgb":[66,74,77]},"05_tracked_graft_tank soft fur":{"rgb":[229,231,222]},"05_tracked_graft_tank ivory eye mask":{"rgb":[243,242,229]},"05_tracked_graft_tank machined edge":{"rgb":[216,221,218]},"05_tracked_graft_tank smoky iris":{"rgb":[132,153,142]},"05_tracked_graft_tank dark steel":{"rgb":[101,108,108]},"05_tracked_graft_tank split beak":{"rgb":[211,209,191]},"05_tracked_graft_tank ear velvet":{"rgb":[153,155,149]},"05_tracked_graft_tank track rubber":{"rgb":[46,51,53]}}},{"name":"Swarm_06_BlueOrange","height":7,"position":[14,0,-21],"parts":[{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_machined_e_e5d17_01","material":"06_blue_orange_hydraulic machined edges"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_machined_e_e5d17_02","material":"06_blue_orange_hydraulic machined edges"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_recesses_89189_01","material":"06_blue_orange_hydraulic recesses"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_warm_paint_0318f_01","material":"06_blue_orange_hydraulic warm painted alloy"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_satin_pale_06aa4_01","material":"06_blue_orange_hydraulic satin pale alloy"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_recessed_g_e71f0_01","material":"06_blue_orange_hydraulic recessed gunmetal"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_soft_fur_80500_01","material":"06_blue_orange_hydraulic soft fur"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_machined_e_0f8ca_01","material":"06_blue_orange_hydraulic machined edge"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_ivory_eye__e90d9_01","material":"06_blue_orange_hydraulic ivory eye mask"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_dark_steel_c788d_01","material":"06_blue_orange_hydraulic dark steel"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_smoky_iris_0db52_01","material":"06_blue_orange_hydraulic smoky iris"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_split_beak_0fdf4_01","material":"06_blue_orange_hydraulic split beak"},{"name":"Swarm_06_BlueOrange__06_blue_orange_hydraulic_ear_velvet_95da6_01","material":"06_blue_orange_hydraulic ear velvet"}],"materials":{"06_blue_orange_hydraulic recesses":{"rgb":[33,38,41]},"06_blue_orange_hydraulic warm painted alloy":{"rgb":[175,177,170]},"06_blue_orange_hydraulic satin pale alloy":{"rgb":[184,189,189]},"06_blue_orange_hydraulic machined edges":{"rgb":[208,211,205]},"06_blue_orange_hydraulic recessed gunmetal":{"rgb":[66,74,77]},"06_blue_orange_hydraulic soft fur":{"rgb":[44,184,208]},"06_blue_orange_hydraulic machined edge":{"rgb":[216,221,218]},"06_blue_orange_hydraulic ivory eye mask":{"rgb":[243,242,229]},"06_blue_orange_hydraulic dark steel":{"rgb":[101,108,108]},"06_blue_orange_hydraulic smoky iris":{"rgb":[132,153,142]},"06_blue_orange_hydraulic split beak":{"rgb":[253,205,44]},"06_blue_orange_hydraulic ear velvet":{"rgb":[249,158,72]}}},{"name":"Swarm_07_NavyRed","height":7,"position":[-27,0,-24],"parts":[{"name":"Swarm_07_NavyRed__07_navy_red_star_machined_edges_84049_01","material":"07_navy_red_star machined edges"},{"name":"Swarm_07_NavyRed__07_navy_red_star_machined_edges_84049_02","material":"07_navy_red_star machined edges"},{"name":"Swarm_07_NavyRed__07_navy_red_star_recesses_afe21_01","material":"07_navy_red_star recesses"},{"name":"Swarm_07_NavyRed__07_navy_red_star_warm_painted_alloy_2737b_01","material":"07_navy_red_star warm painted alloy"},{"name":"Swarm_07_NavyRed__07_navy_red_star_soft_fur_90ad1_01","material":"07_navy_red_star soft fur"},{"name":"Swarm_07_NavyRed__07_navy_red_star_machined_edge_17a20_01","material":"07_navy_red_star machined edge"},{"name":"Swarm_07_NavyRed__07_navy_red_star_ivory_eye_mask_3e265_01","material":"07_navy_red_star ivory eye mask"},{"name":"Swarm_07_NavyRed__07_navy_red_star_vermilion_enamel_73de7_01","material":"07_navy_red_star vermilion enamel"},{"name":"Swarm_07_NavyRed__07_navy_red_star_satin_pale_alloy_950a6_01","material":"07_navy_red_star satin pale alloy"},{"name":"Swarm_07_NavyRed__07_navy_red_star_dark_steel_5ea81_01","material":"07_navy_red_star dark steel"},{"name":"Swarm_07_NavyRed__07_navy_red_star_smoky_iris_8375f_01","material":"07_navy_red_star smoky iris"},{"name":"Swarm_07_NavyRed__07_navy_red_star_split_beak_58eeb_01","material":"07_navy_red_star split beak"},{"name":"Swarm_07_NavyRed__07_navy_red_star_recessed_gunmetal_c0bd0_01","material":"07_navy_red_star recessed gunmetal"},{"name":"Swarm_07_NavyRed__07_navy_red_star_ear_velvet_b59dc_01","material":"07_navy_red_star ear velvet"}],"materials":{"07_navy_red_star recesses":{"rgb":[33,38,41]},"07_navy_red_star warm painted alloy":{"rgb":[175,177,170]},"07_navy_red_star machined edges":{"rgb":[208,211,205]},"07_navy_red_star soft fur":{"rgb":[18,44,80]},"07_navy_red_star machined edge":{"rgb":[216,221,218]},"07_navy_red_star ivory eye mask":{"rgb":[243,242,229]},"07_navy_red_star vermilion enamel":{"rgb":[215,36,44]},"07_navy_red_star satin pale alloy":{"rgb":[184,189,189]},"07_navy_red_star dark steel":{"rgb":[101,108,108]},"07_navy_red_star smoky iris":{"rgb":[132,153,142]},"07_navy_red_star split beak":{"rgb":[215,218,214]},"07_navy_red_star recessed gunmetal":{"rgb":[66,74,77]},"07_navy_red_star ear velvet":{"rgb":[226,31,48]}}},{"name":"Swarm_08_BlueRed","height":7,"position":[28,0,-21],"parts":[{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_machined_e_efb3c_01","material":"08_blue_red_cheek_gunner machined edges"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_machined_e_efb3c_02","material":"08_blue_red_cheek_gunner machined edges"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_machined_e_efb3c_03","material":"08_blue_red_cheek_gunner machined edges"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_recesses_b8713_01","material":"08_blue_red_cheek_gunner recesses"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_warm_paint_46bf0_01","material":"08_blue_red_cheek_gunner warm painted alloy"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_machined_e_15e19_01","material":"08_blue_red_cheek_gunner machined edge"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_soft_fur_43990_01","material":"08_blue_red_cheek_gunner soft fur"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_recessed_g_e5326_01","material":"08_blue_red_cheek_gunner recessed gunmetal"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_satin_pale_77408_01","material":"08_blue_red_cheek_gunner satin pale alloy"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_ivory_eye__493e4_01","material":"08_blue_red_cheek_gunner ivory eye mask"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_vermilion__47ed3_01","material":"08_blue_red_cheek_gunner vermilion enamel"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_dark_steel_4354a_01","material":"08_blue_red_cheek_gunner dark steel"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_smoky_iris_f5b6e_01","material":"08_blue_red_cheek_gunner smoky iris"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_warm_pale__49834_01","material":"08_blue_red_cheek_gunner warm pale paws"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_split_beak_bcf41_01","material":"08_blue_red_cheek_gunner split beak"},{"name":"Swarm_08_BlueRed__08_blue_red_cheek_gunner_ear_velvet_ad868_01","material":"08_blue_red_cheek_gunner ear velvet"}],"materials":{"08_blue_red_cheek_gunner recesses":{"rgb":[33,38,41]},"08_blue_red_cheek_gunner warm painted alloy":{"rgb":[175,177,170]},"08_blue_red_cheek_gunner machined edges":{"rgb":[208,211,205]},"08_blue_red_cheek_gunner machined edge":{"rgb":[216,221,218]},"08_blue_red_cheek_gunner soft fur":{"rgb":[29,184,216]},"08_blue_red_cheek_gunner recessed gunmetal":{"rgb":[66,74,77]},"08_blue_red_cheek_gunner satin pale alloy":{"rgb":[184,189,189]},"08_blue_red_cheek_gunner ivory eye mask":{"rgb":[243,242,229]},"08_blue_red_cheek_gunner vermilion enamel":{"rgb":[215,36,44]},"08_blue_red_cheek_gunner dark steel":{"rgb":[101,108,108]},"08_blue_red_cheek_gunner smoky iris":{"rgb":[132,153,142]},"08_blue_red_cheek_gunner warm pale paws":{"rgb":[241,241,229]},"08_blue_red_cheek_gunner split beak":{"rgb":[222,226,218]},"08_blue_red_cheek_gunner ear velvet":{"rgb":[232,34,50]}}},{"name":"Swarm_09_ArmoredCrawler","height":7,"position":[0,0,-27],"parts":[{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_machined_e_e30c9_01","material":"09 Video Armored Crawler machined edges"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_warm_paint_ce9bb_01","material":"09 Video Armored Crawler warm painted alloy"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_dark_steel_19519_01","material":"09 Video Armored Crawler dark steel"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_recesses_ae8bb_01","material":"09 Video Armored Crawler recesses"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_soft_fur_d9679_01","material":"09 Video Armored Crawler soft fur"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_ivory_eye__90df6_01","material":"09 Video Armored Crawler ivory eye mask"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_smoky_iris_0fde1_01","material":"09 Video Armored Crawler smoky iris"},{"name":"Swarm_09_ArmoredCrawler__09_Video_Armored_Crawler_split_beak_ab4ca_01","material":"09 Video Armored Crawler split beak"}],"materials":{"09 Video Armored Crawler machined edges":{"rgb":[208,211,205]},"09 Video Armored Crawler warm painted alloy":{"rgb":[175,177,170]},"09 Video Armored Crawler dark steel":{"rgb":[101,108,108]},"09 Video Armored Crawler recesses":{"rgb":[33,38,41]},"09 Video Armored Crawler soft fur":{"rgb":[232,232,227]},"09 Video Armored Crawler ivory eye mask":{"rgb":[243,242,229]},"09 Video Armored Crawler smoky iris":{"rgb":[132,153,142]},"09 Video Armored Crawler split beak":{"rgb":[192,194,184]}}}]]==])
local OLD_NAMES = {}
for _, asset in ASSETS do table.insert(OLD_NAMES, asset.name) end
local SOURCE_BLEND = "BIPCI_All_10_Characters.blend"
local EXPECTED_TOTAL = 131
local GROUND_Y = 0.08

local arena = workspace:FindFirstChild("BIPCI_Arena")
assert(arena, "VALIDATION FAILED: Workspace.BIPCI_Arena is missing")
local characters = arena:FindFirstChild("Characters")
assert(characters and characters:IsA("Folder"), "VALIDATION FAILED: BIPCI_Arena.Characters Folder is missing")

-- Phase 1: constrain discovery to this import bundle. Studio may truncate long
-- FBX names with "...", so exact names win and hash/chunk suffixes are fallback IDs.
local importBundle = workspace:FindFirstChild("BIPCI_All_10_Characters")
assert(importBundle, "VALIDATION FAILED: Workspace.BIPCI_All_10_Characters is missing")
local bundleMeshCount = 0
for _, descendant in importBundle:GetDescendants() do
    if descendant:IsA("MeshPart") then bundleMeshCount += 1 end
end
assert(bundleMeshCount == EXPECTED_TOTAL,
    ("VALIDATION FAILED: import bundle expected %d MeshParts; found %d"):format(EXPECTED_TOTAL, bundleMeshCount))

local expectedTotal = 0
local validated = {}
for _, asset in ASSETS do
    assert(type(asset.height) == "number" and asset.height == asset.height and asset.height > 0 and asset.height < math.huge,
        ("VALIDATION FAILED: %s has an invalid target height"):format(tostring(asset.name)))
    local semantic = importBundle:FindFirstChild(asset.name, true)
    assert(semantic, ("VALIDATION FAILED: semantic import container %s is missing"):format(asset.name))
    local semanticMeshCount = 0
    for _, descendant in semantic:GetDescendants() do
        if descendant:IsA("MeshPart") then semanticMeshCount += 1 end
    end
    assert(semanticMeshCount == #asset.parts,
        ("VALIDATION FAILED: %s expected %d MeshParts; found %d"):format(asset.name, #asset.parts, semanticMeshCount))
    local exact, token = {}, {}
    for _, descendant in semantic:GetDescendants() do
        if descendant:IsA("MeshPart") then
            exact[descendant.Name] = exact[descendant.Name] or {}
            table.insert(exact[descendant.Name], descendant)
            local hash, chunk = string.match(descendant.Name, "_([0-9a-f]+)_(%d+)$")
            if hash and chunk then
                local key = hash .. "_" .. chunk
                token[key] = token[key] or {}
                table.insert(token[key], descendant)
            end
        end
    end
    local found = {}
    local used = {}
    for _, spec in asset.parts do
        expectedTotal += 1
        local matches = exact[spec.name]
        if not matches then
            local hash, chunk = string.match(spec.name, "_([0-9a-f]+)_(%d+)$")
            assert(hash and chunk, ("VALIDATION FAILED: canonical chunk token missing in %s"):format(spec.name))
            matches = token[hash .. "_" .. chunk]
        end
        assert(matches, ("VALIDATION FAILED: missing exact/token MeshPart %s under %s"):format(spec.name, asset.name))
        assert(#matches == 1, ("VALIDATION FAILED: expected exactly one %s; found %d"):format(spec.name, #matches))
        local part = matches[1]
        assert(not used[part], ("VALIDATION FAILED: imported MeshPart matched twice: %s"):format(part.Name))
        used[part] = true
        assert(part.Size.X > 0 and part.Size.Y > 0 and part.Size.Z > 0,
            ("VALIDATION FAILED: %s has a non-positive Size"):format(spec.name))
        local materialInfo = asset.materials and asset.materials[spec.material]
        local rgb = materialInfo and materialInfo.rgb
        assert(type(rgb) == "table" and #rgb == 3
            and type(rgb[1]) == "number" and type(rgb[2]) == "number" and type(rgb[3]) == "number",
            ("VALIDATION FAILED: missing/invalid sRGB for %s / %s"):format(asset.name, tostring(spec.material)))
        for channel = 1, 3 do
            assert(rgb[channel] >= 0 and rgb[channel] <= 255,
                ("VALIDATION FAILED: out-of-range sRGB for %s / %s"):format(asset.name, tostring(spec.material)))
        end
        table.insert(found, { part = part, spec = spec, materialInfo = materialInfo })
    end
    assert(#found == #asset.parts, ("VALIDATION FAILED: %s expected %d parts; found %d"):format(asset.name, #asset.parts, #found))
    validated[asset.name] = found
end
assert(expectedTotal == EXPECTED_TOTAL, ("VALIDATION FAILED: game-ready manifest expected %d parts; found %d"):format(EXPECTED_TOTAL, expectedTotal))

for _, oldName in OLD_NAMES do
    local old = characters:FindFirstChild(oldName)
    assert(old and old:IsA("Model"), ("VALIDATION FAILED: old blockout Model %s is missing"):format(oldName))
end

local function materialFor(name)
    local lower = string.lower(name)
    if string.find(lower, "fur", 1, true)
        or string.find(lower, "plush", 1, true)
        or string.find(lower, "fibre", 1, true)
        or string.find(lower, "fabric", 1, true) then
        return Enum.Material.Fabric
    end
    if string.find(lower, "metal", 1, true)
        or string.find(lower, "steel", 1, true)
        or string.find(lower, "iron", 1, true)
        or string.find(lower, "chrome", 1, true)
        or string.find(lower, "bracket", 1, true)
        or string.find(lower, "screw", 1, true)
        or string.find(lower, "hardware", 1, true) then
        return Enum.Material.Metal
    end
    return Enum.Material.SmoothPlastic
end

local function characterType(name)
    if name == "Furbomek_Boss_F069" then return "FurbomekBoss" end
    if string.find(name, "Cudgel_Tank", 1, true) then return "CudgelTank" end
    return "SwarmBot"
end

ChangeHistoryService:SetWaypoint("Before BIPCI character replacement")

-- Phase 2: every potentially failing source check is complete; preserve old content.
local stamp = os.date("!%Y%m%dT%H%M%SZ")
local archive = Instance.new("Folder")
archive.Name = "BIPCI_Character_Archive_" .. stamp
archive.Parent = ServerStorage
for _, oldName in OLD_NAMES do
    characters[oldName].Parent = archive
end

local report = {
    ok = true,
    expected_mesh_parts = expectedTotal,
    game_ready = true,
    archive_path = archive:GetFullName(),
    models = {},
}
local created = {}

for index, asset in ASSETS do
    local model = Instance.new("Model")
    model.Name = asset.name
    model:SetAttribute("SourceBlend", SOURCE_BLEND)
    model:SetAttribute("CharacterType", characterType(asset.name))
    model:SetAttribute("EditableBlockout", false)
    local specID = asset.name == "Furbomek_Boss_F069" and "F069"
        or (string.find(asset.name, "Cudgel_Tank", 1, true) and "05")
        or string.match(asset.name, "Swarm_(%d+)_")
    model:SetAttribute("ModelSpecID", specID)
    model:SetAttribute("Faction", "BIPCI")
    model:SetAttribute("GameReady", true)

    for _, item in validated[asset.name] do
        local part = item.part
        local materialInfo = item.materialInfo

        -- Reparenting retains the imported world CFrame.
        part:SetAttribute("CanonicalChunkName", item.spec.name)
        part.Parent = model
        part.Anchored = true
        part.CanCollide = false
        part.CanQuery = true
        part.CanTouch = false
        part.RenderFidelity = Enum.RenderFidelity.Automatic
        pcall(function() part.CollisionFidelity = Enum.CollisionFidelity.Box end)
        part.Color = Color3.fromRGB(materialInfo.rgb[1], materialInfo.rgb[2], materialInfo.rgb[3])
        part.Material = materialFor(item.spec.material)
        pcall(function() part.DoubleSided = true end)
    end

    model.Parent = characters
    local _, initialSize = model:GetBoundingBox()
    assert(initialSize.Y > 0.001, ("BUILD FAILED: %s has zero-height bounds"):format(asset.name))
    model:ScaleTo(model:GetScale() * asset.height / initialSize.Y)

    local boundsCF, boundsSize = model:GetBoundingBox()
    local target = Vector3.new(asset.position[1], asset.height * 0.5 + GROUND_Y, asset.position[3])
    local delta = target - boundsCF.Position
    model:PivotTo(CFrame.new(delta) * model:GetPivot())

    local root = Instance.new("Part")
    root.Name = "CharacterRoot"
    root.Size = Vector3.new(0.25, 0.25, 0.25)
    root.Transparency = 1
    root.Anchored = true
    root.CanCollide = false
    root.CanQuery = false
    root.CanTouch = false
    root.CFrame = model:GetPivot()
    root.Parent = model
    model.PrimaryPart = root

    local finalCF, finalSize = model:GetBoundingBox()
    table.insert(report.models, {
        name = asset.name,
        mesh_count = #validated[asset.name],
        target_height = asset.height,
        actual_height = finalSize.Y,
        position = { x = finalCF.Position.X, y = finalCF.Position.Y, z = finalCF.Position.Z },
    })
    table.insert(created, model)
end

ChangeHistoryService:SetWaypoint("After BIPCI character replacement")
local boss = characters:FindFirstChild("Furbomek_Boss_F069")
if boss then pcall(function() Selection:Set({ boss }) end) end

print(HttpService:JSONEncode(report))
return HttpService:JSONEncode(report)
