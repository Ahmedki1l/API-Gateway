USE [master]
GO
/****** Object:  Database [damanat_pms]    Script Date: 4/14/2026 3:30:43 PM ******/
CREATE DATABASE [damanat_pms]
 CONTAINMENT = NONE
 GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [damanat_pms].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [damanat_pms] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [damanat_pms] SET ANSI_NULLS OFF 
GO
ALTER DATABASE [damanat_pms] SET ANSI_PADDING OFF 
GO
ALTER DATABASE [damanat_pms] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [damanat_pms] SET ARITHABORT OFF 
GO
ALTER DATABASE [damanat_pms] SET AUTO_CLOSE OFF 
GO
ALTER DATABASE [damanat_pms] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [damanat_pms] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [damanat_pms] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [damanat_pms] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [damanat_pms] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [damanat_pms] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [damanat_pms] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [damanat_pms] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [damanat_pms] SET  ENABLE_BROKER 
GO
ALTER DATABASE [damanat_pms] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [damanat_pms] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [damanat_pms] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [damanat_pms] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [damanat_pms] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [damanat_pms] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [damanat_pms] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [damanat_pms] SET RECOVERY FULL 
GO
ALTER DATABASE [damanat_pms] SET  MULTI_USER 
GO
ALTER DATABASE [damanat_pms] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [damanat_pms] SET DB_CHAINING OFF 
GO
ALTER DATABASE [damanat_pms] SET FILESTREAM( NON_TRANSACTED_ACCESS = OFF ) 
GO
ALTER DATABASE [damanat_pms] SET TARGET_RECOVERY_TIME = 60 SECONDS 
GO
ALTER DATABASE [damanat_pms] SET DELAYED_DURABILITY = DISABLED 
GO
ALTER DATABASE [damanat_pms] SET QUERY_STORE = ON
GO
ALTER DATABASE [damanat_pms] SET QUERY_STORE (OPERATION_MODE = READ_WRITE, CLEANUP_POLICY = (STALE_QUERY_THRESHOLD_DAYS = 30), DATA_FLUSH_INTERVAL_SECONDS = 900, INTERVAL_LENGTH_MINUTES = 60, MAX_STORAGE_SIZE_MB = 1000, QUERY_CAPTURE_MODE = AUTO, SIZE_BASED_CLEANUP_MODE = AUTO)
GO
USE [damanat_pms]
GO
ALTER DATABASE SCOPED CONFIGURATION SET ACCELERATED_PLAN_FORCING = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET ASYNC_STATS_UPDATE_WAIT_AT_LOW_PRIORITY = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET BATCH_MODE_ADAPTIVE_JOINS = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET BATCH_MODE_MEMORY_GRANT_FEEDBACK = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET BATCH_MODE_ON_ROWSTORE = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET CE_FEEDBACK = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET CE_FEEDBACK_FOR_EXPRESSIONS = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET DEFERRED_COMPILATION_TV = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET DOP_FEEDBACK = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET ELEVATE_ONLINE = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET ELEVATE_RESUMABLE = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET EXEC_QUERY_STATS_FOR_SCALAR_FUNCTIONS = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET FORCE_SHOWPLAN_RUNTIME_PARAMETER_COLLECTION = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET FULLTEXT_INDEX_VERSION = 2;
GO
ALTER DATABASE SCOPED CONFIGURATION SET GLOBAL_TEMPORARY_TABLE_AUTO_DROP = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET IDENTITY_CACHE = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET INTERLEAVED_EXECUTION_TVF = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET ISOLATE_SECURITY_POLICY_CARDINALITY = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET LAST_QUERY_PLAN_STATS = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET LEDGER_DIGEST_STORAGE_ENDPOINT = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET LEGACY_CARDINALITY_ESTIMATION = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION FOR SECONDARY SET LEGACY_CARDINALITY_ESTIMATION = PRIMARY;
GO
ALTER DATABASE SCOPED CONFIGURATION SET LIGHTWEIGHT_QUERY_PROFILING = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET MAXDOP = 0;
GO
ALTER DATABASE SCOPED CONFIGURATION FOR SECONDARY SET MAXDOP = PRIMARY;
GO
ALTER DATABASE SCOPED CONFIGURATION SET MEMORY_GRANT_FEEDBACK_PERCENTILE_GRANT = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET MEMORY_GRANT_FEEDBACK_PERSISTENCE = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET OPTIMIZED_PLAN_FORCING = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET OPTIMIZED_SP_EXECUTESQL = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET OPTIMIZE_FOR_AD_HOC_WORKLOADS = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET OPTIONAL_PARAMETER_OPTIMIZATION = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET PARAMETER_SENSITIVE_PLAN_OPTIMIZATION = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET PARAMETER_SNIFFING = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION FOR SECONDARY SET PARAMETER_SNIFFING = PRIMARY;
GO
ALTER DATABASE SCOPED CONFIGURATION SET PAUSED_RESUMABLE_INDEX_ABORT_DURATION_MINUTES = 1440;
GO
ALTER DATABASE SCOPED CONFIGURATION SET PREVIEW_FEATURES = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET QUERY_OPTIMIZER_HOTFIXES = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION FOR SECONDARY SET QUERY_OPTIMIZER_HOTFIXES = PRIMARY;
GO
ALTER DATABASE SCOPED CONFIGURATION SET READABLE_SECONDARY_TEMPORARY_STATS_AUTO_CREATE = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET READABLE_SECONDARY_TEMPORARY_STATS_AUTO_UPDATE = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET ROW_MODE_MEMORY_GRANT_FEEDBACK = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET TSQL_SCALAR_UDF_INLINING = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET VERBOSE_TRUNCATION_WARNINGS = ON;
GO
ALTER DATABASE SCOPED CONFIGURATION SET XTP_PROCEDURE_EXECUTION_STATISTICS = OFF;
GO
ALTER DATABASE SCOPED CONFIGURATION SET XTP_QUERY_EXECUTION_STATISTICS = OFF;
GO
USE [damanat_pms]
GO
/****** Object:  Table [dbo].[alembic_version]    Script Date: 4/14/2026 3:30:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[alembic_version](
	[version_num] [varchar](32) NOT NULL,
 CONSTRAINT [alembic_version_pkc] PRIMARY KEY CLUSTERED 
(
	[version_num] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[alerts]    Script Date: 4/14/2026 3:30:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[alerts](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[alert_type] [varchar](50) NOT NULL,
	[camera_id] [varchar](50) NOT NULL,
	[zone_id] [varchar](100) NULL,
	[zone_name] [varchar](100) NULL,
	[region_id] [int] NULL,
	[slot_number] [varchar](100) NULL,
	[event_type] [varchar](100) NULL,
	[description] [varchar](max) NULL,
	[snapshot_path] [varchar](max) NULL,
	[is_test] [bit] NOT NULL,
	[is_resolved] [bit] NOT NULL,
	[triggered_at] [datetime] NOT NULL,
	[resolved_at] [datetime] NULL,
	[plate_number] [varchar](50) NULL,
	[severity] [varchar](20) NOT NULL,
	[location_display] [varchar](255) NULL,
	[slot_id] [varchar](50) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[entry_exit_log]    Script Date: 4/14/2026 3:30:43 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[entry_exit_log](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[plate_number] [varchar](50) NOT NULL,
	[vehicle_id] [int] NULL,
	[vehicle_type] [varchar](50) NULL,
	[gate] [varchar](20) NOT NULL,
	[camera_id] [varchar](50) NOT NULL,
	[event_time] [datetime] NOT NULL,
	[parking_duration] [int] NULL,
	[snapshot_path] [varchar](max) NULL,
	[matched_entry_id] [int] NULL,
	[is_test] [bit] NOT NULL,
	[created_at] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[intrusions]    Script Date: 4/14/2026 3:30:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[intrusions](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[slot_id] [varchar](50) NOT NULL,
	[plate_number] [varchar](20) NULL,
	[status] [varchar](20) NULL,
	[detected_at] [datetime] NULL,
	[resolved_at] [datetime] NULL,
	[camera_id] [varchar](50) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[parking_sessions]    Script Date: 4/14/2026 3:30:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[parking_sessions](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[plate_number] [varchar](50) NOT NULL,
	[vehicle_id] [int] NULL,
	[vehicle_type] [varchar](50) NULL,
	[is_employee] [bit] NOT NULL,
	[entry_time] [datetime] NOT NULL,
	[exit_time] [datetime] NULL,
	[duration_seconds] [int] NULL,
	[entry_camera_id] [varchar](50) NOT NULL,
	[exit_camera_id] [varchar](50) NULL,
	[entry_snapshot_path] [varchar](max) NULL,
	[exit_snapshot_path] [varchar](max) NULL,
	[floor] [varchar](50) NULL,
	[zone_id] [varchar](100) NULL,
	[zone_name] [varchar](100) NULL,
	[slot_number] [varchar](100) NULL,
	[parked_at] [datetime] NULL,
	[slot_left_at] [datetime] NULL,
	[slot_camera_id] [varchar](50) NULL,
	[slot_snapshot_path] [varchar](max) NULL,
	[status] [varchar](20) NOT NULL,
	[created_at] [datetime] NOT NULL,
	[updated_at] [datetime] NOT NULL,
	[slot_id] [varchar](50) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[parking_slots]    Script Date: 4/14/2026 3:30:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[parking_slots](
	[slot_id] [varchar](50) NOT NULL,
	[slot_name] [varchar](100) NULL,
	[floor] [varchar](50) NULL,
	[polygon] [nvarchar](max) NULL,
	[is_available] [bit] NULL,
	[is_violation_zone] [bit] NULL,
	[zone_id] [varchar](100) NULL,
	[zone_name] [varchar](100) NULL,
PRIMARY KEY CLUSTERED 
(
	[slot_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[slot_status]    Script Date: 4/14/2026 3:30:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[slot_status](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[slot_id] [varchar](50) NOT NULL,
	[plate_number] [varchar](20) NULL,
	[status] [varchar](20) NULL,
	[time] [datetime] NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]
GO
/****** Object:  Table [dbo].[vehicles]    Script Date: 4/14/2026 3:30:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[vehicles](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[plate_number] [varchar](50) NOT NULL,
	[owner_name] [varchar](200) NOT NULL,
	[vehicle_type] [varchar](50) NOT NULL,
	[employee_id] [varchar](100) NULL,
	[is_registered] [bit] NOT NULL,
	[registered_at] [datetime] NULL,
	[notes] [varchar](max) NULL,
	[title] [varchar](50) NOT NULL,
	[is_employee] [bit] NOT NULL,
	[phone] [varchar](50) NULL,
	[email] [varchar](255) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[zone_occupancy]    Script Date: 4/14/2026 3:30:44 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[zone_occupancy](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[zone_id] [varchar](100) NOT NULL,
	[camera_id] [varchar](50) NOT NULL,
	[current_count] [int] NOT NULL,
	[max_capacity] [int] NOT NULL,
	[last_updated] [datetime] NULL,
	[zone_name] [varchar](100) NULL,
	[floor] [varchar](50) NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]
GO
INSERT [dbo].[alembic_version] ([version_num]) VALUES (N'7a8b9c0d1e2f')
SET IDENTITY_INSERT [dbo].[alerts] ON 

INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'entry', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate EEB-80', NULL, 0, 1, CAST(N'2026-04-01T06:24:07.997' AS DateTime), CAST(N'2026-04-12T13:32:10.850' AS DateTime), NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (2, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'entry', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate SHR-1198', NULL, 0, 1, CAST(N'2026-04-01T06:34:44.097' AS DateTime), CAST(N'2026-04-12T13:32:13.397' AS DateTime), NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (3, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'entry', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate BGD-7593', NULL, 0, 1, CAST(N'2026-04-01T06:37:32.143' AS DateTime), CAST(N'2026-04-12T13:32:15.370' AS DateTime), NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (4, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'entry', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate HDU-7', NULL, 0, 1, CAST(N'2026-04-02T06:34:38.063' AS DateTime), CAST(N'2026-04-12T17:43:10.177' AS DateTime), NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (5, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'entry', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate NJS-7894', NULL, 0, 0, CAST(N'2026-04-02T07:13:54.757' AS DateTime), NULL, NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (9, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'entry', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate HVA-77', NULL, 0, 0, CAST(N'2026-04-02T08:23:40.783' AS DateTime), NULL, NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1006, N'violation', N'UNKNOWN', N'V1_Violation_1', N'Slot V1 Violation 1', NULL, NULL, N'vehicle_detected', N'Unauthorized vehicle detected in V1_Violation_1', NULL, 0, 1, CAST(N'2026-04-11T12:52:19.357' AS DateTime), CAST(N'2026-04-12T10:53:13.563' AS DateTime), NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1007, N'violation', N'UNKNOWN', N'V2_Violation_2', N'Slot V2 Violation 2', NULL, NULL, N'vehicle_detected', N'Unauthorized vehicle detected in V2_Violation_2', NULL, 0, 1, CAST(N'2026-04-11T12:52:19.637' AS DateTime), CAST(N'2026-04-12T10:53:13.630' AS DateTime), NULL, N'warning', NULL, NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1015, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate ZRS-6511', NULL, 0, 0, CAST(N'2026-04-13T05:44:34.390' AS DateTime), NULL, N'ZRS-6511', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1016, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate AAD-2560', NULL, 0, 0, CAST(N'2026-04-13T05:47:07.553' AS DateTime), NULL, N'AAD-2560', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1017, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate HGD-2926', NULL, 0, 0, CAST(N'2026-04-13T05:50:11.273' AS DateTime), NULL, N'HGD-2926', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1018, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate UEU-777', NULL, 0, 0, CAST(N'2026-04-13T05:50:20.137' AS DateTime), NULL, N'UEU-777', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1019, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate TTB-8627', NULL, 0, 0, CAST(N'2026-04-13T05:50:32.220' AS DateTime), NULL, N'TTB-8627', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1020, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate KKR-2994', N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055235_397226.jpg', 0, 0, CAST(N'2026-04-13T05:52:38.560' AS DateTime), NULL, N'KKR-2994', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1021, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate SHR-1198', N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055923_066242.jpg', 0, 0, CAST(N'2026-04-13T05:59:27.113' AS DateTime), NULL, N'SHR-1198', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1022, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate NDD-4141', NULL, 0, 0, CAST(N'2026-04-13T06:06:08.057' AS DateTime), NULL, N'NDD-4141', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1023, N'unknown_vehicle', N'CAM-EXIT', N'exit', N'Exit Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at exit gate: plate HBR-4920', N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-EXIT_20260413_060709_927038.jpg', 0, 0, CAST(N'2026-04-13T06:07:12.543' AS DateTime), NULL, N'HBR-4920', N'critical', N'Exit Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1024, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate RTB-2016', NULL, 0, 0, CAST(N'2026-04-13T06:10:40.460' AS DateTime), NULL, N'RTB-2016', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1025, N'capacity_exceeded', N'CAM-09', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 100% (9/9)', NULL, 0, 0, CAST(N'2026-04-13T06:11:18.610' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1026, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate RGR-6466', NULL, 0, 0, CAST(N'2026-04-14T05:06:52.127' AS DateTime), NULL, N'RGR-6466', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1033, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate HGD-2926', NULL, 0, 0, CAST(N'2026-04-14T05:11:23.130' AS DateTime), NULL, N'HGD-2926', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1036, N'capacity_exceeded', N'CAM-09', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 111% (10/9)', NULL, 0, 0, CAST(N'2026-04-14T05:12:27.957' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1037, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate SDD-6707', NULL, 0, 0, CAST(N'2026-04-14T05:35:48.107' AS DateTime), NULL, N'SDD-6707', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1038, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate NXR-2727', NULL, 0, 0, CAST(N'2026-04-14T05:37:17.820' AS DateTime), NULL, N'NXR-2727', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1039, N'capacity_exceeded', N'CAM-09', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 122% (11/9)', NULL, 0, 0, CAST(N'2026-04-14T05:40:26.883' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1040, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate AAD-2560', NULL, 0, 0, CAST(N'2026-04-14T05:46:29.787' AS DateTime), NULL, N'AAD-2560', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1041, N'capacity_exceeded', N'CAM-09', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 133% (12/9)', NULL, 0, 0, CAST(N'2026-04-14T05:47:31.967' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1043, N'capacity_exceeded', N'CAM-09', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 144% (13/9)', NULL, 0, 0, CAST(N'2026-04-14T05:48:29.623' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1044, N'capacity_exceeded', N'CAM-10', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 133% (12/9)', NULL, 0, 0, CAST(N'2026-04-14T05:48:38.217' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1045, N'violation', N'CAM_01', N'GF-FRONT', N'GF-FRONT', NULL, N'Slot V1 Violation 1', N'vehicle_detected', N'Unauthorized vehicle detected in Slot V1 Violation 1', NULL, 0, 1, CAST(N'2026-04-14T05:49:09.723' AS DateTime), CAST(N'2026-04-14T08:11:45.150' AS DateTime), N'', N'critical', NULL, N'V1_Violation_1')
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1046, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate EEB-80', NULL, 0, 0, CAST(N'2026-04-14T05:51:33.940' AS DateTime), NULL, N'EEB-80', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1047, N'unknown_vehicle', N'CAM-ENTRY', N'entry', N'Entry Gate', NULL, NULL, N'AccessControllerEvent', N'Unregistered vehicle at entry gate: plate RDJ-9640', NULL, 0, 0, CAST(N'2026-04-14T10:27:20.633' AS DateTime), NULL, N'RDJ-9640', N'critical', N'Entry Gate', NULL)
INSERT [dbo].[alerts] ([id], [alert_type], [camera_id], [zone_id], [zone_name], [region_id], [slot_number], [event_type], [description], [snapshot_path], [is_test], [is_resolved], [triggered_at], [resolved_at], [plate_number], [severity], [location_display], [slot_id]) VALUES (1048, N'capacity_exceeded', N'CAM-09', N'B2-PARKING', N'B2 Parking', NULL, NULL, N'occupancy_update', N'Zone B2-PARKING is nearly full: 144% (13/9)', NULL, 0, 0, CAST(N'2026-04-14T10:27:59.963' AS DateTime), NULL, NULL, N'warning', N'B2 Parking', NULL)
SET IDENTITY_INSERT [dbo].[alerts] OFF
SET IDENTITY_INSERT [dbo].[entry_exit_log] ON 

INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1, N'EEB-80', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-01T09:24:05.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-01T06:24:07.993' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (2, N'SHR-1198', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-01T09:34:42.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-01T06:34:44.093' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (3, N'BGD-7593', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-01T09:37:30.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-01T06:37:32.143' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (4, N'HDU-7', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-02T09:34:34.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-02T06:34:38.063' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (5, N'NJS-7894', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-02T10:13:51.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-02T07:13:54.757' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (6, N'TRS-9117', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-02T11:13:02.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-02T08:13:07.957' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (7, N'SHR-1198', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-02T11:15:55.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-02T08:16:01.043' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (8, N'HVA-77', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-02T11:23:35.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-02T08:23:40.783' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1006, N'ZRS-6511', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:44:32.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T05:44:34.353' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1007, N'AAD-2560', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:47:05.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T05:47:07.510' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1008, N'HGD-2926', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:50:09.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T05:50:11.253' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1009, N'UEU-777', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:50:17.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T05:50:20.120' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1010, N'TTB-8627', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:50:30.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T05:50:32.213' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1011, N'KKR-2994', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:52:27.430' AS DateTime), NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055235_397226.jpg', NULL, 0, CAST(N'2026-04-13T05:52:38.540' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1012, N'SHR-1198', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T08:59:13.117' AS DateTime), NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055923_066242.jpg', NULL, 0, CAST(N'2026-04-13T05:59:27.087' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1013, N'NDD-4141', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T09:06:02.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T06:06:07.227' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1014, N'HBR-4920', NULL, N'unknown', N'exit', N'CAM-EXIT', CAST(N'2026-04-13T09:07:07.513' AS DateTime), NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-EXIT_20260413_060709_927038.jpg', NULL, 0, CAST(N'2026-04-13T06:07:12.527' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1015, N'RTB-2016', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-13T09:10:38.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-13T06:10:40.440' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1016, N'RGR-6466', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:06:46.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:06:52.093' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1017, N'HGD-2926', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:11:21.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:11:23.117' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1018, N'SDD-6707', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:35:45.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:35:48.077' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1019, N'NXR-2727', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:37:16.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:37:17.767' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1020, N'AAD-2560', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:46:28.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:46:29.770' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1021, N'SHR-1198', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:47:53.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:47:55.097' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1022, N'EEB-80', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T08:51:30.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T05:51:33.923' AS DateTime))
INSERT [dbo].[entry_exit_log] ([id], [plate_number], [vehicle_id], [vehicle_type], [gate], [camera_id], [event_time], [parking_duration], [snapshot_path], [matched_entry_id], [is_test], [created_at]) VALUES (1023, N'RDJ-9640', NULL, N'unknown', N'entry', N'CAM-ENTRY', CAST(N'2026-04-14T13:27:16.000' AS DateTime), NULL, NULL, NULL, 0, CAST(N'2026-04-14T10:27:20.593' AS DateTime))
SET IDENTITY_INSERT [dbo].[entry_exit_log] OFF
SET IDENTITY_INSERT [dbo].[intrusions] ON 

INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (1, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-30T14:35:56.557' AS DateTime), CAST(N'2026-03-30T15:08:48.753' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (2, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-03-30T14:35:57.067' AS DateTime), CAST(N'2026-03-30T15:08:32.213' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (3, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-03-30T15:08:35.617' AS DateTime), CAST(N'2026-03-31T10:27:09.937' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (4, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-30T15:11:33.383' AS DateTime), CAST(N'2026-03-30T15:11:41.677' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (5, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-30T15:14:20.287' AS DateTime), CAST(N'2026-03-31T17:56:57.630' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (6, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-03-31T10:35:51.460' AS DateTime), CAST(N'2026-03-31T10:36:19.463' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (7, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-03-31T12:30:00.313' AS DateTime), CAST(N'2026-03-31T12:31:53.813' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (8, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-03-31T12:40:42.393' AS DateTime), CAST(N'2026-04-01T06:24:04.720' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (9, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-31T18:13:47.000' AS DateTime), CAST(N'2026-03-31T18:14:10.553' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (10, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-31T18:18:16.503' AS DateTime), CAST(N'2026-03-31T18:18:37.083' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (11, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-31T18:28:28.227' AS DateTime), CAST(N'2026-03-31T18:28:32.677' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (12, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-31T18:30:24.460' AS DateTime), CAST(N'2026-03-31T18:30:29.823' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (13, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-03-31T18:37:42.727' AS DateTime), CAST(N'2026-03-31T18:37:49.110' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (14, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-01T06:32:25.060' AS DateTime), CAST(N'2026-04-01T06:37:35.423' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (15, N'V2_Violation_2', N'SHR-1198', N'resolved', CAST(N'2026-04-01T06:35:00.867' AS DateTime), CAST(N'2026-04-01T06:35:09.347' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (16, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-04-01T06:35:31.057' AS DateTime), CAST(N'2026-04-01T06:37:57.207' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (17, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T06:28:19.953' AS DateTime), CAST(N'2026-04-02T06:28:27.430' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (18, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T06:29:07.957' AS DateTime), CAST(N'2026-04-02T06:31:51.277' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (19, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-04-02T06:38:55.527' AS DateTime), CAST(N'2026-04-02T06:39:10.827' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (20, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-04-02T06:41:17.520' AS DateTime), CAST(N'2026-04-02T07:03:43.360' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (21, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-04-02T07:05:12.040' AS DateTime), CAST(N'2026-04-02T07:05:35.627' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (22, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T07:05:33.920' AS DateTime), CAST(N'2026-04-02T07:05:40.033' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (23, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-04-02T07:11:27.470' AS DateTime), CAST(N'2026-04-02T07:11:39.083' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (24, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T07:13:55.830' AS DateTime), CAST(N'2026-04-02T07:14:03.500' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (25, N'V2_Violation_2', N'', N'resolved', CAST(N'2026-04-02T07:14:54.550' AS DateTime), CAST(N'2026-04-02T07:16:36.910' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (26, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T07:15:01.683' AS DateTime), CAST(N'2026-04-02T07:16:01.637' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (27, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T07:16:12.940' AS DateTime), CAST(N'2026-04-02T07:16:39.050' AS DateTime), NULL)
INSERT [dbo].[intrusions] ([id], [slot_id], [plate_number], [status], [detected_at], [resolved_at], [camera_id]) VALUES (28, N'V1_Violation_1', N'', N'resolved', CAST(N'2026-04-02T07:29:53.733' AS DateTime), CAST(N'2026-04-02T07:30:13.907' AS DateTime), NULL)
SET IDENTITY_INSERT [dbo].[intrusions] OFF
SET IDENTITY_INSERT [dbo].[parking_sessions] ON 

INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (8, N'ZRS-6511', NULL, N'unknown', 0, CAST(N'2026-04-13T08:44:32.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:44:34.367' AS DateTime), CAST(N'2026-04-13T05:44:34.367' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (9, N'AAD-2560', NULL, N'unknown', 0, CAST(N'2026-04-13T08:47:05.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:47:07.540' AS DateTime), CAST(N'2026-04-14T05:46:29.783' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (10, N'HGD-2926', NULL, N'unknown', 0, CAST(N'2026-04-13T08:50:09.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:50:11.260' AS DateTime), CAST(N'2026-04-14T05:11:23.130' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (11, N'UEU-777', NULL, N'unknown', 0, CAST(N'2026-04-13T08:50:17.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:50:20.127' AS DateTime), CAST(N'2026-04-13T05:50:20.127' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (12, N'TTB-8627', NULL, N'unknown', 0, CAST(N'2026-04-13T08:50:30.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:50:32.217' AS DateTime), CAST(N'2026-04-13T05:50:32.217' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (13, N'KKR-2994', NULL, N'unknown', 0, CAST(N'2026-04-13T08:52:27.430' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055235_397226.jpg', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:52:38.550' AS DateTime), CAST(N'2026-04-13T05:52:38.550' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (14, N'SHR-1198', NULL, N'unknown', 0, CAST(N'2026-04-13T08:59:13.117' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, N'https://cognerax-learn.sfo3.cdn.digitaloceanspaces.com/detection_images/part_ANPR_CAM-ENTRY_20260413_055923_066242.jpg', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T05:59:27.097' AS DateTime), CAST(N'2026-04-14T05:47:55.107' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (15, N'NDD-4141', NULL, N'unknown', 0, CAST(N'2026-04-13T09:06:02.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T06:06:07.403' AS DateTime), CAST(N'2026-04-13T06:06:07.403' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (16, N'RTB-2016', NULL, N'unknown', 0, CAST(N'2026-04-13T09:10:38.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-13T06:10:40.443' AS DateTime), CAST(N'2026-04-13T06:10:40.443' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (17, N'RGR-6466', NULL, N'unknown', 0, CAST(N'2026-04-14T08:06:46.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-14T05:06:52.103' AS DateTime), CAST(N'2026-04-14T05:06:52.103' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (18, N'SDD-6707', NULL, N'unknown', 0, CAST(N'2026-04-14T08:35:45.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-14T05:35:48.087' AS DateTime), CAST(N'2026-04-14T05:35:48.087' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (19, N'NXR-2727', NULL, N'unknown', 0, CAST(N'2026-04-14T08:37:16.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-14T05:37:17.780' AS DateTime), CAST(N'2026-04-14T05:37:17.780' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (20, N'EEB-80', NULL, N'unknown', 0, CAST(N'2026-04-14T08:51:30.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-14T05:51:33.930' AS DateTime), CAST(N'2026-04-14T05:51:33.930' AS DateTime), NULL)
INSERT [dbo].[parking_sessions] ([id], [plate_number], [vehicle_id], [vehicle_type], [is_employee], [entry_time], [exit_time], [duration_seconds], [entry_camera_id], [exit_camera_id], [entry_snapshot_path], [exit_snapshot_path], [floor], [zone_id], [zone_name], [slot_number], [parked_at], [slot_left_at], [slot_camera_id], [slot_snapshot_path], [status], [created_at], [updated_at], [slot_id]) VALUES (21, N'RDJ-9640', NULL, N'unknown', 0, CAST(N'2026-04-14T13:27:16.000' AS DateTime), NULL, NULL, N'CAM-ENTRY', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, N'open', CAST(N'2026-04-14T10:27:20.607' AS DateTime), CAST(N'2026-04-14T10:27:20.607' AS DateTime), NULL)
SET IDENTITY_INSERT [dbo].[parking_sessions] OFF
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B1_CRO', N'Slot B1 CRO', N'B1', N'[[329.0, 97.0], [277.0, 28.0], [381.0, 14.0], [477.0, 76.0], [329.0, 97.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B10_CTO', N'Slot B10 CTO', N'B1', N'[[316.0, 118.0], [418.0, 98.0], [409.0, 150.0], [390.0, 160.0], [316.0, 118.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B11_CFO', N'Slot B11_CFO', N'B1', N'[[573.0, 126.0], [640.0, 136.0], [614.0, 96.0], [554.0, 84.0], [573.0, 126.0]]', 0, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B12', N'Slot B12', N'B1', N'[[170.0, 57.0], [150.0, 41.0], [244.0, 27.0], [268.0, 39.0], [170.0, 57.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B13_COO', N'Slot B13 COO', N'B1', N'[[524.0, 64.0], [408.0, 22.0], [363.0, 29.0], [504.0, 80.0], [524.0, 64.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B14', N'Slot B14', N'B2', N'[[330.0, 58.0], [312.0, 31.0], [362.0, 26.0], [396.0, 54.0], [330.0, 58.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B15', N'Slot B15', N'B2', N'[[411.0, 182.0], [338.0, 66.0], [426.0, 68.0], [478.0, 108.0], [462.0, 184.0], [411.0, 182.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B16', N'Slot B16', N'B2', N'[[410.0, 95.0], [390.0, 62.0], [440.0, 62.0], [483.0, 100.0], [410.0, 95.0]]', 1, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B17', N'Slot B17', N'B2', N'[[445.0, 154.0], [410.0, 98.0], [494.0, 106.0], [552.0, 163.0], [445.0, 154.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B18', N'Slot B18', N'B2', N'[[508.0, 272.0], [452.0, 162.0], [636.0, 174.0], [638.0, 263.0], [508.0, 272.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B19', N'Slot B19', N'B2', N'[[506.0, 281.0], [638.0, 273.0], [638.0, 354.0], [532.0, 356.0], [506.0, 281.0]]', 1, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B2', N'Slot B2', N'B1', N'[[327.0, 245.0], [286.0, 162.0], [674.0, 119.0], [795.0, 179.0], [327.0, 245.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B20', N'Slot B20', N'B2', N'[[79.0, 163.0], [192.0, 94.0], [114.0, 92.0], [2.0, 153.0], [79.0, 163.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B21', N'Slot B21', N'B2', N'[[508.0, 172.0], [404.0, 95.0], [502.0, 101.0], [603.0, 168.0], [508.0, 172.0]]', 1, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B22', N'Slot B22', N'B2', N'[[110.0, 193.0], [109.0, 252.0], [102.0, 316.0], [140.0, 360.0], [481.0, 359.0], [538.0, 232.0], [304.0, 121.0], [110.0, 193.0]]', 1, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B23', N'Slot B23', N'B2', N'[[47.0, 150.0], [141.0, 147.0], [190.0, 87.0], [113.0, 94.0], [47.0, 150.0]]', 1, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B24', N'Slot B24', N'B2', N'[[432.0, 107.0], [348.0, 120.0], [422.0, 151.0], [432.0, 107.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B25', N'Slot B25', N'B2', N'[[186.0, 80.0], [302.0, 65.0], [354.0, 77.0], [214.0, 94.0], [186.0, 80.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B27', N'Slot B27', N'B2', N'[[190.0, 49.0], [177.0, 68.0], [52.0, 83.0], [83.0, 58.0], [190.0, 49.0]]', 0, 0, N'B2-PARKING', N'B2-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B3_CEO', N'Slot B3 CEO', N'B1', N'[[409.0, 403.0], [332.0, 257.0], [802.0, 184.0], [941.0, 272.0], [409.0, 403.0]]', 0, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B6_Reserved', N'Slot B6 Reserved', N'B1', N'[[156.0, 91.0], [250.0, 75.0], [314.0, 122.0], [172.0, 145.0], [156.0, 91.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B8', N'Slot B8', N'B1', N'[[342.0, 51.0], [308.0, 34.0], [370.0, 27.0], [402.0, 41.0], [342.0, 51.0]]', 1, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'B9', N'Slot B9', N'B1', N'[[436.0, 97.0], [348.0, 80.0], [262.0, 135.0], [394.0, 164.0], [436.0, 97.0]]', 0, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'G1', N'G1_SN', N'Ground Floor', N'[[459.0, 466.0], [811.0, 691.0], [1023.0, 379.0], [763.0, 271.0], [459.0, 466.0]]', 0, 0, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'G2', N'Slot G2', N'Ground Floor', N'[[325.0, 307.0], [434.0, 424.0], [701.0, 262.0], [557.0, 205.0], [325.0, 307.0]]', 0, 0, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'G3', N'Slot G3', N'Ground Floor', N'[[315.0, 283.0], [255.0, 228.0], [428.0, 149.0], [519.0, 191.0], [315.0, 283.0]]', 1, 0, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'G4', N'Slot G4', N'Ground Floor', N'[[372.0, 169.0], [448.0, 149.0], [510.0, 214.0], [470.0, 250.0], [372.0, 169.0]]', 1, 0, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'G5', N'Slot G5', N'Ground Floor', N'[[284.0, 200.0], [360.0, 178.0], [450.0, 258.0], [372.0, 310.0], [284.0, 200.0]]', 0, 0, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'G6', N'Slot G6', N'Ground Floor', N'[[149.0, 240.0], [265.0, 209.0], [357.0, 322.0], [290.0, 352.0], [194.0, 351.0], [149.0, 240.0]]', 1, 0, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'GMIA', N'GMIA', N'B1', N'[[305.0, 67.0], [388.0, 100.0], [314.0, 133.0], [305.0, 128.0], [305.0, 67.0]]', 0, 0, N'B1-PARKING', N'B1-PARKING')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'V1_Violation_1', N'Slot V1 Violation 1', N'Ground Floor', N'[[638.0, 84.0], [1058.0, 199.0], [1277.0, 297.0], [1276.0, 390.0], [524.0, 118.0], [638.0, 84.0]]', 1, 1, N'GF-FRONT', N'GF-FRONT')
INSERT [dbo].[parking_slots] ([slot_id], [slot_name], [floor], [polygon], [is_available], [is_violation_zone], [zone_id], [zone_name]) VALUES (N'V2_Violation_2', N'Slot V2 Violation 2', N'Ground Floor', N'[[0.0, 142.0], [173.0, 104.0], [358.0, 80.0], [422.0, 84.0], [450.0, 119.0], [2.0, 208.0], [0.0, 142.0]]', 1, 1, N'GF-FRONT', N'GF-FRONT')
SET IDENTITY_INSERT [dbo].[slot_status] ON 

INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-30T14:35:52.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2, N'B9', N'', N'occupied', CAST(N'2026-03-30T14:35:52.750' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-30T14:35:56.567' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (4, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-30T14:35:57.070' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (5, N'B9', N'', N'occupied', CAST(N'2026-03-30T14:46:27.177' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (6, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-30T15:06:34.190' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (7, N'B9', N'', N'occupied', CAST(N'2026-03-30T15:06:34.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (8, N'V1_Violation_1', N'', N'available', CAST(N'2026-03-30T15:08:32.237' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (9, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-30T15:08:35.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (10, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-30T15:08:38.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (11, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-30T15:08:48.757' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (12, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-30T15:11:33.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (13, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-30T15:11:41.683' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (14, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-30T15:14:20.297' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (16, N'G2', N'', N'occupied', CAST(N'2026-03-31T10:18:20.720' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (17, N'B2', N'', N'occupied', CAST(N'2026-03-31T10:18:20.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (18, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:18:20.840' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (19, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T10:18:20.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (20, N'B9', N'', N'occupied', CAST(N'2026-03-31T10:18:20.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (21, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:18:20.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (22, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:18:21.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (23, N'B23', N'', N'occupied', CAST(N'2026-03-31T10:18:21.127' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (24, N'B24', N'', N'occupied', CAST(N'2026-03-31T10:18:21.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (25, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:18:21.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (26, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:18:21.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (27, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:18:21.727' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (28, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T10:18:21.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (29, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:18:21.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (30, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:18:22.507' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (31, N'B3_CEO', N'', N'available', CAST(N'2026-03-31T10:18:25.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (32, N'B15', N'', N'occupied', CAST(N'2026-03-31T10:18:25.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (33, N'B18', N'', N'available', CAST(N'2026-03-31T10:18:27.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (34, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:18:28.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (35, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:18:31.100' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (36, N'B15', N'', N'available', CAST(N'2026-03-31T10:18:32.053' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (37, N'B14', N'', N'available', CAST(N'2026-03-31T10:18:32.060' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (38, N'B18', N'', N'available', CAST(N'2026-03-31T10:18:34.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (39, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:18:35.163' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (40, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:18:37.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (41, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:18:39.270' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (42, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:18:41.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (43, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:18:43.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (44, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:18:43.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (45, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:18:43.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (46, N'B25', N'', N'available', CAST(N'2026-03-31T10:18:49.657' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (47, N'G3', N'', N'available', CAST(N'2026-03-31T10:18:49.843' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (48, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:18:50.063' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (49, N'G5', N'', N'available', CAST(N'2026-03-31T10:18:51.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (50, N'B6_Reserved', N'', N'available', CAST(N'2026-03-31T10:18:53.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (51, N'B18', N'', N'available', CAST(N'2026-03-31T10:18:54.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (52, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:18:57.263' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (53, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:18:57.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (54, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:18:58.530' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (55, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:18:58.573' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (56, N'B14', N'', N'available', CAST(N'2026-03-31T10:18:59.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (57, N'G3', N'', N'available', CAST(N'2026-03-31T10:19:01.783' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (58, N'G5', N'', N'available', CAST(N'2026-03-31T10:19:01.850' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (59, N'B21', N'', N'occupied', CAST(N'2026-03-31T10:19:03.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (60, N'B25', N'', N'available', CAST(N'2026-03-31T10:19:05.100' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (61, N'B18', N'', N'available', CAST(N'2026-03-31T10:19:05.160' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (62, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:19:06.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (63, N'B21', N'', N'available', CAST(N'2026-03-31T10:19:07.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (64, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:19:07.710' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (65, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:19:08.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (66, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:19:13.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (67, N'B18', N'', N'available', CAST(N'2026-03-31T10:19:18.427' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (68, N'B14', N'', N'available', CAST(N'2026-03-31T10:19:22.620' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (69, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:19:25.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (70, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:19:27.263' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (71, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:19:28.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (72, N'B15', N'', N'occupied', CAST(N'2026-03-31T10:19:30.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (73, N'B25', N'', N'available', CAST(N'2026-03-31T10:19:33.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (74, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:19:35.887' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (75, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T10:19:37.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (76, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:19:38.517' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (77, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:19:40.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (78, N'G3', N'', N'available', CAST(N'2026-03-31T10:19:44.197' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (79, N'G5', N'', N'available', CAST(N'2026-03-31T10:19:44.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (80, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:19:47.473' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (81, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:19:47.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (82, N'B27', N'', N'occupied', CAST(N'2026-03-31T10:19:50.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (83, N'B27', N'', N'available', CAST(N'2026-03-31T10:19:54.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (84, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:19:54.700' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (85, N'B18', N'', N'available', CAST(N'2026-03-31T10:19:59.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (86, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:20:05.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (87, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:20:06.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (88, N'B14', N'', N'available', CAST(N'2026-03-31T10:20:09.287' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (89, N'B18', N'', N'available', CAST(N'2026-03-31T10:20:09.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (90, N'G3', N'', N'available', CAST(N'2026-03-31T10:20:10.157' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (91, N'G5', N'', N'available', CAST(N'2026-03-31T10:20:10.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (92, N'B25', N'', N'available', CAST(N'2026-03-31T10:20:10.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (93, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:20:13.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (94, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:20:13.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (95, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:20:20.440' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (96, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:20:23.787' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (97, N'B15', N'', N'available', CAST(N'2026-03-31T10:20:25.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (98, N'B14', N'', N'available', CAST(N'2026-03-31T10:20:25.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (100, N'G2', N'', N'occupied', CAST(N'2026-03-31T10:21:31.747' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (101, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:21:31.787' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (102, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:21:31.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (103, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T10:21:31.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (104, N'B9', N'', N'occupied', CAST(N'2026-03-31T10:21:31.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (105, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:21:32.000' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (106, N'B23', N'', N'occupied', CAST(N'2026-03-31T10:21:32.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (107, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:21:32.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (108, N'B15', N'', N'occupied', CAST(N'2026-03-31T10:21:32.190' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (109, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:21:32.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (110, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:21:32.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (111, N'B24', N'', N'occupied', CAST(N'2026-03-31T10:21:32.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (112, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T10:21:33.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (113, N'G3', N'', N'available', CAST(N'2026-03-31T10:21:36.140' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (114, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:21:38.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (115, N'G5', N'', N'available', CAST(N'2026-03-31T10:21:41.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (116, N'B18', N'', N'available', CAST(N'2026-03-31T10:21:42.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (117, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:21:43.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (118, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:21:48.690' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (119, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:21:54.710' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (120, N'B2', N'', N'occupied', CAST(N'2026-03-31T10:21:55.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (121, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:21:58.803' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (122, N'B20', N'', N'available', CAST(N'2026-03-31T10:22:02.280' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (123, N'B22', N'', N'available', CAST(N'2026-03-31T10:22:02.357' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (124, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:22:05.670' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (125, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:22:06.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (126, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:22:06.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (127, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:22:10.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (128, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:22:10.833' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (129, N'B18', N'', N'available', CAST(N'2026-03-31T10:22:19.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (130, N'B19', N'', N'available', CAST(N'2026-03-31T10:22:19.683' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (131, N'B20', N'', N'available', CAST(N'2026-03-31T10:22:22.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (132, N'B14', N'', N'available', CAST(N'2026-03-31T10:22:22.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (133, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:22:23.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (134, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:22:25.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (135, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:22:25.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (136, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:22:28.737' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (137, N'G5', N'', N'available', CAST(N'2026-03-31T10:22:31.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (138, N'G3', N'', N'available', CAST(N'2026-03-31T10:22:31.803' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (139, N'B12', N'', N'occupied', CAST(N'2026-03-31T10:22:36.823' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (140, N'B18', N'', N'available', CAST(N'2026-03-31T10:22:39.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (141, N'B19', N'', N'available', CAST(N'2026-03-31T10:22:39.690' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (142, N'B20', N'', N'available', CAST(N'2026-03-31T10:22:40.137' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (143, N'B12', N'', N'available', CAST(N'2026-03-31T10:22:40.363' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (144, N'B14', N'', N'available', CAST(N'2026-03-31T10:22:42.443' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (145, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:22:43.193' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (146, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:22:43.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (147, N'B22', N'', N'available', CAST(N'2026-03-31T10:22:44.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (148, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:22:45.787' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (149, N'B18', N'', N'available', CAST(N'2026-03-31T10:22:49.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (150, N'B19', N'', N'available', CAST(N'2026-03-31T10:22:49.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (151, N'B20', N'', N'available', CAST(N'2026-03-31T10:22:49.937' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (153, N'B2', N'', N'occupied', CAST(N'2026-03-31T10:24:47.420' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (154, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:24:47.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (155, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T10:24:47.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (156, N'B9', N'', N'occupied', CAST(N'2026-03-31T10:24:47.520' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (157, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:24:47.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (158, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:24:47.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (159, N'B23', N'', N'occupied', CAST(N'2026-03-31T10:24:47.700' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (160, N'B15', N'', N'occupied', CAST(N'2026-03-31T10:24:47.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (161, N'G6', N'', N'occupied', CAST(N'2026-03-31T10:24:47.887' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (162, N'G2', N'', N'occupied', CAST(N'2026-03-31T10:24:48.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (163, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:24:48.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (164, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T10:24:48.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (165, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:24:49.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (166, N'B24', N'', N'occupied', CAST(N'2026-03-31T10:24:49.180' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (167, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:24:49.337' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (168, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:24:49.710' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (169, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:24:53.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (170, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:24:54.340' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (171, N'B14', N'', N'available', CAST(N'2026-03-31T10:24:59.813' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (172, N'B22', N'', N'available', CAST(N'2026-03-31T10:25:02.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (173, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:25:04.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (174, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:25:08.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (175, N'B20', N'', N'available', CAST(N'2026-03-31T10:25:11.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (176, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:25:12.203' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (177, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:25:12.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (178, N'G6', N'', N'available', CAST(N'2026-03-31T10:25:13.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (179, N'B21', N'', N'occupied', CAST(N'2026-03-31T10:25:16.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (180, N'G3', N'', N'available', CAST(N'2026-03-31T10:25:18.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (181, N'B3_CEO', N'', N'available', CAST(N'2026-03-31T10:25:18.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (182, N'B21', N'', N'available', CAST(N'2026-03-31T10:25:20.480' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (183, N'G5', N'', N'available', CAST(N'2026-03-31T10:25:25.057' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (184, N'B14', N'', N'available', CAST(N'2026-03-31T10:25:25.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (185, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:25:29.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (186, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:25:39.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (187, N'B20', N'', N'available', CAST(N'2026-03-31T10:25:45.577' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (188, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:25:54.293' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (189, N'B18', N'', N'available', CAST(N'2026-03-31T10:25:56.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (190, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:25:59.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (191, N'B20', N'', N'available', CAST(N'2026-03-31T10:26:02.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (192, N'G6', N'', N'occupied', CAST(N'2026-03-31T10:26:02.847' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (193, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:26:04.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (194, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:26:04.513' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (195, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:26:04.667' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (196, N'B14', N'', N'available', CAST(N'2026-03-31T10:26:05.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (197, N'B20', N'', N'available', CAST(N'2026-03-31T10:26:08.113' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (198, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:26:15.423' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (199, N'B22', N'', N'available', CAST(N'2026-03-31T10:26:17.910' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (200, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:26:21.720' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (201, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:26:21.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (203, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:26:25.303' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (204, N'B20', N'', N'available', CAST(N'2026-03-31T10:26:25.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (205, N'B25', N'', N'available', CAST(N'2026-03-31T10:26:25.937' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (206, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:26:26.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (207, N'B14', N'', N'available', CAST(N'2026-03-31T10:26:30.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (208, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:26:34.503' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (209, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:26:34.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (210, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:26:34.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (212, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:26:36.457' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (213, N'B12', N'', N'occupied', CAST(N'2026-03-31T10:26:39.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (214, N'B22', N'', N'available', CAST(N'2026-03-31T10:26:40.417' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (215, N'B14', N'', N'available', CAST(N'2026-03-31T10:26:40.460' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (216, N'B12', N'', N'available', CAST(N'2026-03-31T10:26:43.250' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (217, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:26:46.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (218, N'B22', N'', N'available', CAST(N'2026-03-31T10:26:57.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (219, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-31T10:26:59.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (221, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:27:00.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (222, N'B25', N'', N'available', CAST(N'2026-03-31T10:27:02.350' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (223, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:27:02.693' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (224, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:27:05.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (225, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:27:05.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (226, N'G3', N'', N'available', CAST(N'2026-03-31T10:27:07.133' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (227, N'G5', N'', N'available', CAST(N'2026-03-31T10:27:07.197' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (229, N'V1_Violation_1', N'', N'available', CAST(N'2026-03-31T10:27:09.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (230, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:27:11.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (231, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:27:14.583' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (232, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:27:15.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (233, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:27:16.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (234, N'B14', N'', N'available', CAST(N'2026-03-31T10:27:17.843' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (235, N'B18', N'', N'available', CAST(N'2026-03-31T10:27:23.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (236, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:27:24.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (237, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:27:31.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (238, N'B18', N'', N'available', CAST(N'2026-03-31T10:27:40.670' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (239, N'B19', N'', N'available', CAST(N'2026-03-31T10:27:40.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (240, N'B22', N'', N'available', CAST(N'2026-03-31T10:27:40.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (241, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:27:44.167' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (242, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:27:44.583' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (243, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:27:44.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (244, N'B14', N'', N'available', CAST(N'2026-03-31T10:27:45.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (245, N'B18', N'', N'available', CAST(N'2026-03-31T10:27:49.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (246, N'B19', N'', N'available', CAST(N'2026-03-31T10:27:49.437' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (247, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:27:54.383' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (248, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:27:56.863' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (249, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:27:59.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (250, N'B18', N'', N'available', CAST(N'2026-03-31T10:28:03.487' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (251, N'B19', N'', N'available', CAST(N'2026-03-31T10:28:03.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (252, N'B22', N'', N'available', CAST(N'2026-03-31T10:28:03.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (253, N'B21', N'', N'occupied', CAST(N'2026-03-31T10:28:04.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (254, N'B21', N'', N'available', CAST(N'2026-03-31T10:28:08.313' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (255, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:28:09.177' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (256, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:28:09.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (257, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:28:09.267' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (258, N'B14', N'', N'available', CAST(N'2026-03-31T10:28:10.623' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (259, N'B19', N'', N'available', CAST(N'2026-03-31T10:28:13.247' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (260, N'B3_CEO', N'', N'available', CAST(N'2026-03-31T10:28:14.483' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (261, N'G3', N'', N'available', CAST(N'2026-03-31T10:28:14.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (262, N'G5', N'', N'available', CAST(N'2026-03-31T10:28:14.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (263, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:28:16.647' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (264, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:28:16.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (265, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:28:18.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (266, N'B18', N'', N'available', CAST(N'2026-03-31T10:28:20.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (267, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:28:21.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (268, N'G6', N'', N'available', CAST(N'2026-03-31T10:28:22.157' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (269, N'G5', N'', N'available', CAST(N'2026-03-31T10:28:22.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (270, N'B20', N'', N'available', CAST(N'2026-03-31T10:28:25.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (271, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:28:26.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (272, N'G6', N'', N'occupied', CAST(N'2026-03-31T10:28:47.033' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (273, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:28:54.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (274, N'B20', N'', N'available', CAST(N'2026-03-31T10:29:00.703' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (276, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:34:47.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (277, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T10:34:48.013' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (278, N'B9', N'', N'occupied', CAST(N'2026-03-31T10:34:48.060' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (279, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:34:48.137' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (280, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:34:48.187' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (281, N'B23', N'', N'occupied', CAST(N'2026-03-31T10:34:48.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (282, N'B15', N'', N'occupied', CAST(N'2026-03-31T10:34:48.313' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (283, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:34:48.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (284, N'B27', N'', N'occupied', CAST(N'2026-03-31T10:34:48.327' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (285, N'G6', N'', N'occupied', CAST(N'2026-03-31T10:34:48.407' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (286, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:34:48.520' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (287, N'G3', N'', N'occupied', CAST(N'2026-03-31T10:34:48.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (288, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T10:34:48.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (289, N'B2', N'', N'occupied', CAST(N'2026-03-31T10:34:49.013' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (290, N'B24', N'', N'occupied', CAST(N'2026-03-31T10:34:49.157' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (291, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:34:58.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (292, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:34:58.833' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (293, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:34:58.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (294, N'B20', N'', N'available', CAST(N'2026-03-31T10:35:00.180' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (295, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:35:03.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (296, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:35:04.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (298, N'B27', N'', N'available', CAST(N'2026-03-31T10:35:08.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (300, N'B22', N'', N'available', CAST(N'2026-03-31T10:35:13.417' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (301, N'B27', N'', N'occupied', CAST(N'2026-03-31T10:35:14.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (302, N'B3_CEO', N'', N'available', CAST(N'2026-03-31T10:35:14.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (303, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:35:17.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (304, N'B20', N'', N'available', CAST(N'2026-03-31T10:35:17.897' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (305, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:35:20.583' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (306, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:35:20.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (307, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:35:24.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (308, N'B24', N'', N'available', CAST(N'2026-03-31T10:35:24.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (309, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:35:25.760' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (310, N'G3', N'', N'available', CAST(N'2026-03-31T10:35:27.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (311, N'G5', N'', N'available', CAST(N'2026-03-31T10:35:27.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (312, N'B24', N'', N'occupied', CAST(N'2026-03-31T10:35:28.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (313, N'B20', N'', N'available', CAST(N'2026-03-31T10:35:29.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (314, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:35:31.727' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (315, N'B22', N'', N'available', CAST(N'2026-03-31T10:35:42.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (317, N'B3_CEO', N'', N'available', CAST(N'2026-03-31T10:35:46.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (318, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:35:49.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (319, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-31T10:35:51.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (320, N'B21', N'', N'occupied', CAST(N'2026-03-31T10:35:52.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (321, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:35:52.903' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (323, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:35:56.530' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (324, N'B18', N'', N'available', CAST(N'2026-03-31T10:35:58.443' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (325, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:35:58.803' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (326, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:36:03.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (327, N'B22', N'', N'available', CAST(N'2026-03-31T10:36:04.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (328, N'B21', N'', N'available', CAST(N'2026-03-31T10:36:04.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (329, N'B19', N'', N'available', CAST(N'2026-03-31T10:36:06.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (330, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:36:06.780' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (331, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:36:09.190' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (332, N'B21', N'', N'occupied', CAST(N'2026-03-31T10:36:10.080' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (334, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:36:10.993' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (335, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T10:36:12.750' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (337, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:36:14.573' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (338, N'B21', N'', N'available', CAST(N'2026-03-31T10:36:15.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (341, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:36:19.200' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (342, N'V1_Violation_1', N'', N'available', CAST(N'2026-03-31T10:36:19.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (344, N'B2', N'', N'occupied', CAST(N'2026-03-31T10:40:44.050' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (345, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T10:40:44.057' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (346, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T10:40:44.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (347, N'B9', N'', N'occupied', CAST(N'2026-03-31T10:40:44.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (348, N'B25', N'', N'occupied', CAST(N'2026-03-31T10:40:44.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (349, N'B23', N'', N'occupied', CAST(N'2026-03-31T10:40:44.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (350, N'B15', N'', N'occupied', CAST(N'2026-03-31T10:40:44.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (351, N'B14', N'', N'occupied', CAST(N'2026-03-31T10:40:44.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (352, N'B27', N'', N'occupied', CAST(N'2026-03-31T10:40:44.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (353, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T10:40:45.003' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (354, N'G4', N'', N'occupied', CAST(N'2026-03-31T10:40:45.420' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (355, N'G5', N'', N'occupied', CAST(N'2026-03-31T10:40:45.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (356, N'G6', N'', N'occupied', CAST(N'2026-03-31T10:40:45.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (357, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:40:46.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (358, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:40:46.177' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (359, N'B24', N'', N'occupied', CAST(N'2026-03-31T10:40:46.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (360, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:40:48.993' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (362, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:40:53.647' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (363, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:40:54.427' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (364, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T10:40:55.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (365, N'B20', N'', N'available', CAST(N'2026-03-31T10:40:56.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (366, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:40:58.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (369, N'B20', N'', N'occupied', CAST(N'2026-03-31T10:41:14.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (371, N'B20', N'', N'available', CAST(N'2026-03-31T10:41:28.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (374, N'B2', N'', N'available', CAST(N'2026-03-31T10:41:40.887' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (375, N'B22', N'', N'available', CAST(N'2026-03-31T10:41:41.720' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (376, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:41:47.113' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (377, N'B22', N'', N'occupied', CAST(N'2026-03-31T10:41:50.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (378, N'B18', N'', N'available', CAST(N'2026-03-31T10:41:51.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (379, N'B19', N'', N'available', CAST(N'2026-03-31T10:41:51.907' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (380, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:41:53.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (381, N'B18', N'', N'occupied', CAST(N'2026-03-31T10:41:54.540' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (382, N'B19', N'', N'occupied', CAST(N'2026-03-31T10:41:54.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (383, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T10:41:57.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (384, N'B13_COO', N'', N'available', CAST(N'2026-03-31T10:42:01.327' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (386, N'B22', N'', N'available', CAST(N'2026-03-31T10:42:05.533' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (388, N'G2', N'', N'occupied', CAST(N'2026-03-31T12:30:00.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (389, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-31T12:30:00.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (390, N'G5', N'', N'occupied', CAST(N'2026-03-31T12:30:00.383' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (391, N'B2', N'', N'occupied', CAST(N'2026-03-31T12:30:00.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (392, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T12:30:00.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (393, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T12:30:00.520' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (394, N'B9', N'', N'occupied', CAST(N'2026-03-31T12:30:00.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (395, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:30:00.673' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (396, N'B22', N'', N'occupied', CAST(N'2026-03-31T12:30:00.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (397, N'B14', N'', N'occupied', CAST(N'2026-03-31T12:30:00.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (398, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T12:30:02.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (399, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T12:30:02.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (400, N'B1_CRO', N'', N'occupied', CAST(N'2026-03-31T12:30:06.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (401, N'B22', N'', N'available', CAST(N'2026-03-31T12:30:17.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (402, N'B22', N'', N'occupied', CAST(N'2026-03-31T12:30:20.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (403, N'G6', N'', N'occupied', CAST(N'2026-03-31T12:31:17.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (404, N'B25', N'', N'occupied', CAST(N'2026-03-31T12:31:24.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (405, N'B18', N'', N'occupied', CAST(N'2026-03-31T12:31:26.620' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (406, N'B20', N'', N'occupied', CAST(N'2026-03-31T12:31:26.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (407, N'B15', N'', N'occupied', CAST(N'2026-03-31T12:31:26.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (408, N'G6', N'', N'available', CAST(N'2026-03-31T12:31:27.397' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (409, N'B20', N'', N'available', CAST(N'2026-03-31T12:31:32.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (410, N'B15', N'', N'available', CAST(N'2026-03-31T12:31:32.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (411, N'B18', N'', N'available', CAST(N'2026-03-31T12:31:34.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (412, N'G6', N'', N'occupied', CAST(N'2026-03-31T12:31:34.533' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (413, N'B25', N'', N'available', CAST(N'2026-03-31T12:31:36.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (414, N'V1_Violation_1', N'', N'available', CAST(N'2026-03-31T12:31:53.823' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (415, N'B10_CTO', N'', N'available', CAST(N'2026-03-31T12:31:56.283' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (416, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T12:32:01.530' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (417, N'G2', N'', N'occupied', CAST(N'2026-03-31T12:33:29.623' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (418, N'G5', N'', N'occupied', CAST(N'2026-03-31T12:33:29.700' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (419, N'B2', N'', N'occupied', CAST(N'2026-03-31T12:33:29.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (420, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T12:33:29.807' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (421, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T12:33:29.853' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (422, N'B9', N'', N'occupied', CAST(N'2026-03-31T12:33:29.910' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (423, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:33:29.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (424, N'B22', N'', N'occupied', CAST(N'2026-03-31T12:33:30.107' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (425, N'B14', N'', N'occupied', CAST(N'2026-03-31T12:33:30.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (426, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T12:33:30.280' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (427, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T12:33:31.443' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (428, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T12:33:40.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (429, N'B13_COO', N'', N'available', CAST(N'2026-03-31T12:33:44.397' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (430, N'B3_CEO', N'', N'available', CAST(N'2026-03-31T12:33:47.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (431, N'G5', N'', N'occupied', CAST(N'2026-03-31T12:35:29.250' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (432, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T12:35:29.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (433, N'B9', N'', N'occupied', CAST(N'2026-03-31T12:35:29.490' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (434, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T12:35:29.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (435, N'B18', N'', N'occupied', CAST(N'2026-03-31T12:35:29.683' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (436, N'B19', N'', N'occupied', CAST(N'2026-03-31T12:35:29.693' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (437, N'B21', N'', N'occupied', CAST(N'2026-03-31T12:35:29.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (438, N'B22', N'', N'occupied', CAST(N'2026-03-31T12:35:29.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (439, N'B15', N'', N'occupied', CAST(N'2026-03-31T12:35:29.853' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (440, N'G6', N'', N'occupied', CAST(N'2026-03-31T12:35:29.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (441, N'G2', N'', N'occupied', CAST(N'2026-03-31T12:35:30.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (442, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T12:35:30.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (443, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T12:35:30.857' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (444, N'B14', N'', N'occupied', CAST(N'2026-03-31T12:35:31.157' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (445, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T12:35:31.340' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (446, N'B2', N'', N'occupied', CAST(N'2026-03-31T12:35:31.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (447, N'B20', N'', N'occupied', CAST(N'2026-03-31T12:35:36.163' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (448, N'G2', N'', N'available', CAST(N'2026-03-31T12:35:42.450' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (449, N'B22', N'', N'available', CAST(N'2026-03-31T12:35:42.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (450, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:35:43.387' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (451, N'G2', N'', N'occupied', CAST(N'2026-03-31T12:35:45.610' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (452, N'B20', N'', N'available', CAST(N'2026-03-31T12:35:50.007' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (453, N'B13_COO', N'', N'available', CAST(N'2026-03-31T12:35:51.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (454, N'B24', N'', N'available', CAST(N'2026-03-31T12:35:51.990' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (455, N'B18', N'', N'available', CAST(N'2026-03-31T12:35:55.160' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (456, N'B19', N'', N'available', CAST(N'2026-03-31T12:35:55.167' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (457, N'B21', N'', N'available', CAST(N'2026-03-31T12:35:55.227' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (458, N'B18', N'', N'occupied', CAST(N'2026-03-31T12:35:58.230' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (459, N'B19', N'', N'occupied', CAST(N'2026-03-31T12:35:58.250' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (460, N'B20', N'', N'occupied', CAST(N'2026-03-31T12:35:58.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (461, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:36:00.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (462, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T12:36:02.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (463, N'B20', N'', N'available', CAST(N'2026-03-31T12:36:03.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (464, N'B21', N'', N'occupied', CAST(N'2026-03-31T12:36:03.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (465, N'B24', N'', N'available', CAST(N'2026-03-31T12:36:07.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (466, N'B13_COO', N'', N'available', CAST(N'2026-03-31T12:36:08.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (467, N'B19', N'', N'available', CAST(N'2026-03-31T12:36:10.007' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (468, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:36:10.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (469, N'B21', N'', N'available', CAST(N'2026-03-31T12:36:10.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (470, N'B18', N'', N'available', CAST(N'2026-03-31T12:36:12.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (471, N'B14', N'', N'available', CAST(N'2026-03-31T12:36:12.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (472, N'B18', N'', N'occupied', CAST(N'2026-03-31T12:36:15.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (473, N'B19', N'', N'occupied', CAST(N'2026-03-31T12:36:15.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (474, N'B14', N'', N'occupied', CAST(N'2026-03-31T12:36:16.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (475, N'B20', N'', N'occupied', CAST(N'2026-03-31T12:36:18.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (476, N'B24', N'', N'available', CAST(N'2026-03-31T12:36:19.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (477, N'B21', N'', N'occupied', CAST(N'2026-03-31T12:36:21.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (478, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T12:36:25.977' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (479, N'B22', N'', N'occupied', CAST(N'2026-03-31T12:36:27.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (480, N'B20', N'', N'available', CAST(N'2026-03-31T12:36:30.820' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (481, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:36:32.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (482, N'B24', N'', N'available', CAST(N'2026-03-31T12:36:42.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (483, N'B18', N'', N'available', CAST(N'2026-03-31T12:36:44.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (484, N'B19', N'', N'available', CAST(N'2026-03-31T12:36:44.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (485, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:36:46.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (486, N'B22', N'', N'available', CAST(N'2026-03-31T12:36:50.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (487, N'B21', N'', N'available', CAST(N'2026-03-31T12:36:51.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (488, N'B14', N'', N'available', CAST(N'2026-03-31T12:36:53.220' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (489, N'B18', N'', N'occupied', CAST(N'2026-03-31T12:36:55.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (490, N'B24', N'', N'available', CAST(N'2026-03-31T12:37:00.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (491, N'B19', N'', N'occupied', CAST(N'2026-03-31T12:37:00.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (492, N'B20', N'', N'occupied', CAST(N'2026-03-31T12:37:01.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (493, N'B14', N'', N'occupied', CAST(N'2026-03-31T12:37:02.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (494, N'G5', N'', N'occupied', CAST(N'2026-03-31T12:40:12.760' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (495, N'B10_CTO', N'', N'occupied', CAST(N'2026-03-31T12:40:12.817' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (496, N'B3_CEO', N'', N'occupied', CAST(N'2026-03-31T12:40:12.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (497, N'B6_Reserved', N'', N'occupied', CAST(N'2026-03-31T12:40:12.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (498, N'B9', N'', N'occupied', CAST(N'2026-03-31T12:40:12.993' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (499, N'B24', N'', N'occupied', CAST(N'2026-03-31T12:40:13.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (500, N'B20', N'', N'occupied', CAST(N'2026-03-31T12:40:13.230' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (501, N'B15', N'', N'occupied', CAST(N'2026-03-31T12:40:13.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (502, N'B14', N'', N'occupied', CAST(N'2026-03-31T12:40:13.423' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (503, N'G6', N'', N'occupied', CAST(N'2026-03-31T12:40:13.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (504, N'G2', N'', N'occupied', CAST(N'2026-03-31T12:40:14.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (505, N'B18', N'', N'occupied', CAST(N'2026-03-31T12:40:16.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (506, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T12:40:17.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (507, N'B13_COO', N'', N'occupied', CAST(N'2026-03-31T12:40:17.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (508, N'B22', N'', N'occupied', CAST(N'2026-03-31T12:40:23.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (509, N'B21', N'', N'occupied', CAST(N'2026-03-31T12:40:23.937' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (510, N'B24', N'', N'available', CAST(N'2026-03-31T12:40:25.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (511, N'B19', N'', N'occupied', CAST(N'2026-03-31T12:40:29.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (512, N'B19', N'', N'available', CAST(N'2026-03-31T12:40:36.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (513, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-03-31T12:40:42.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (514, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T12:40:42.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (515, N'B18', N'', N'available', CAST(N'2026-03-31T12:40:44.520' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (516, N'B2', N'', N'occupied', CAST(N'2026-03-31T12:40:44.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (517, N'B11_CFO', N'', N'available', CAST(N'2026-03-31T12:40:49.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (518, N'B15', N'', N'available', CAST(N'2026-03-31T12:40:51.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (519, N'B11_CFO', N'', N'occupied', CAST(N'2026-03-31T12:40:52.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (520, N'B21', N'', N'available', CAST(N'2026-03-31T12:40:53.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (521, N'B27', N'', N'occupied', CAST(N'2026-03-31T12:40:57.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (522, N'B21', N'', N'occupied', CAST(N'2026-03-31T12:40:58.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (523, N'G4', N'', N'occupied', CAST(N'2026-03-31T12:41:00.367' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (524, N'B27', N'', N'available', CAST(N'2026-03-31T12:41:01.347' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (525, N'G6', N'', N'available', CAST(N'2026-03-31T12:41:01.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (526, N'B27', N'', N'occupied', CAST(N'2026-03-31T12:41:05.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (527, N'B2', N'', N'available', CAST(N'2026-03-31T12:41:05.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (528, N'B27', N'', N'available', CAST(N'2026-03-31T12:41:09.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (529, N'G2', N'', N'occupied', CAST(N'2026-03-31T17:56:26.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (530, N'G6', N'', N'occupied', CAST(N'2026-03-31T17:56:26.180' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (531, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T17:56:52.757' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (532, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-31T17:56:57.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (533, N'G6', N'', N'occupied', CAST(N'2026-03-31T18:02:48.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (534, N'G2', N'', N'occupied', CAST(N'2026-03-31T18:13:03.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (535, N'G6', N'', N'occupied', CAST(N'2026-03-31T18:13:03.717' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (536, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T18:13:47.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (537, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-31T18:14:10.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (538, N'G2', N'', N'occupied', CAST(N'2026-03-31T18:17:01.683' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (539, N'G6', N'', N'occupied', CAST(N'2026-03-31T18:17:02.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (540, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T18:18:16.517' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (541, N'G6', N'', N'available', CAST(N'2026-03-31T18:18:22.503' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (542, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-31T18:18:37.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (543, N'G2', N'', N'occupied', CAST(N'2026-03-31T18:27:35.690' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (544, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T18:28:28.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (545, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-31T18:28:32.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (546, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T18:30:24.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (547, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-31T18:30:29.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (548, N'G2', N'', N'occupied', CAST(N'2026-03-31T18:32:56.740' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (549, N'G2', N'', N'occupied', CAST(N'2026-03-31T18:36:39.817' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (550, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-03-31T18:37:42.740' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (551, N'V2_Violation_2', N'', N'available', CAST(N'2026-03-31T18:37:49.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (552, N'G2', N'', N'occupied', CAST(N'2026-03-31T18:41:54.337' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (553, N'G2', N'', N'occupied', CAST(N'2026-03-31T19:36:11.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (555, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:19:41.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (556, N'B2', N'', N'occupied', CAST(N'2026-04-01T06:19:41.583' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (557, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:19:41.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (558, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-01T06:19:41.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (559, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T06:19:41.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (560, N'B9', N'', N'occupied', CAST(N'2026-04-01T06:19:41.807' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (561, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:19:41.820' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (562, N'B25', N'', N'occupied', CAST(N'2026-04-01T06:19:41.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (563, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:19:42.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (564, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:19:42.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (565, N'G6', N'', N'occupied', CAST(N'2026-04-01T06:19:42.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (566, N'G2', N'', N'occupied', CAST(N'2026-04-01T06:19:42.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (567, N'B1_CRO', N'', N'available', CAST(N'2026-04-01T06:20:05.720' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (568, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:20:07.780' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (569, N'B8', N'', N'available', CAST(N'2026-04-01T06:20:12.283' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (570, N'B21', N'', N'available', CAST(N'2026-04-01T06:20:19.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (571, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:20:27.780' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (572, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T06:20:29.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (573, N'B21', N'', N'available', CAST(N'2026-04-01T06:20:36.457' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (574, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:20:38.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (575, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:20:45.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (576, N'B21', N'', N'available', CAST(N'2026-04-01T06:21:06.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (577, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:21:14.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (578, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T06:21:16.760' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (579, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:21:20.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (580, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:21:38.503' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (581, N'B21', N'', N'available', CAST(N'2026-04-01T06:21:51.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (582, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:21:52.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (583, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:21:59.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (584, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:22:13.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (585, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:22:18.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (586, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:22:38.803' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (587, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:23:01.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (588, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:23:32.757' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (589, N'B3_CEO', N'', N'available', CAST(N'2026-04-01T06:23:35.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (590, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:23:38.270' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (591, N'B3_CEO', N'', N'available', CAST(N'2026-04-01T06:23:42.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (592, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:23:46.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (593, N'B21', N'', N'available', CAST(N'2026-04-01T06:23:47.197' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (594, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:23:47.897' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (595, N'B3_CEO', N'', N'available', CAST(N'2026-04-01T06:23:51.813' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (596, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:23:52.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (597, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:23:56.287' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (598, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:23:57.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (599, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-01T06:24:00.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (600, N'B3_CEO', N'', N'available', CAST(N'2026-04-01T06:24:01.070' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (601, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-01T06:24:04.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (602, N'B21', N'', N'available', CAST(N'2026-04-01T06:24:15.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (603, N'B21', N'EEB-80', N'occupied', CAST(N'2026-04-01T06:24:18.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (604, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:24:22.190' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (605, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:24:24.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (606, N'B14', N'', N'available', CAST(N'2026-04-01T06:24:28.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (607, N'B21', N'', N'available', CAST(N'2026-04-01T06:24:31.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (608, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:24:32.213' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (609, N'B2', N'', N'available', CAST(N'2026-04-01T06:24:35.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (610, N'B3_CEO', N'', N'available', CAST(N'2026-04-01T06:24:35.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (611, N'B21', N'', N'occupied', CAST(N'2026-04-01T06:24:35.420' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (612, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:24:43.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (613, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:24:50.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (614, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T06:24:52.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (615, N'B14', N'', N'available', CAST(N'2026-04-01T06:24:55.990' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (616, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:24:59.723' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (617, N'B8', N'', N'available', CAST(N'2026-04-01T06:25:01.673' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (618, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:25:01.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (619, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:25:08.747' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (620, N'B2', N'', N'occupied', CAST(N'2026-04-01T06:25:10.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (621, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:25:10.330' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (622, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:25:12.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (623, N'B14', N'', N'available', CAST(N'2026-04-01T06:25:16.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (624, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:25:21.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (625, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:25:22.887' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (626, N'B8', N'', N'available', CAST(N'2026-04-01T06:25:24.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (627, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:25:26.513' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (628, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:25:33.227' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (629, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:25:37.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (630, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:25:39.787' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (631, N'B14', N'', N'available', CAST(N'2026-04-01T06:25:43.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (632, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:25:48.383' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (633, N'B8', N'', N'available', CAST(N'2026-04-01T06:25:52.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (634, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:25:56.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (635, N'B13_COO', N'', N'available', CAST(N'2026-04-01T06:25:59.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (636, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:26:05.287' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (637, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:26:07.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (638, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:26:08.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (639, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:26:10.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (641, N'B2', N'', N'occupied', CAST(N'2026-04-01T06:29:15.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (642, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:29:15.617' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (643, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T06:29:15.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (644, N'B9', N'', N'occupied', CAST(N'2026-04-01T06:29:15.707' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (645, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:29:15.717' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (646, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:29:15.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (647, N'B25', N'', N'occupied', CAST(N'2026-04-01T06:29:15.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (648, N'G6', N'', N'occupied', CAST(N'2026-04-01T06:29:16.053' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (649, N'G2', N'', N'occupied', CAST(N'2026-04-01T06:29:16.483' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (650, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:29:22.623' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (651, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:29:36.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (652, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:29:39.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (653, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:30:20.000' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (654, N'B8', N'', N'available', CAST(N'2026-04-01T06:30:47.330' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (655, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:31:06.187' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (656, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:31:06.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (657, N'B8', N'', N'available', CAST(N'2026-04-01T06:31:13.667' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (658, N'B3_CEO', N'', N'available', CAST(N'2026-04-01T06:31:19.773' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (659, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T06:31:20.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (660, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:31:21.270' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (661, N'G6', N'', N'available', CAST(N'2026-04-01T06:31:23.203' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (662, N'B9', N'', N'available', CAST(N'2026-04-01T06:31:27.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (663, N'B8', N'', N'available', CAST(N'2026-04-01T06:31:37.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (664, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:31:45.483' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (665, N'B9', N'', N'occupied', CAST(N'2026-04-01T06:31:45.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (666, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:31:46.087' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (667, N'G6', N'', N'occupied', CAST(N'2026-04-01T06:31:56.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (668, N'B27', N'', N'occupied', CAST(N'2026-04-01T06:32:02.453' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (669, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:32:12.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (670, N'B15', N'', N'occupied', CAST(N'2026-04-01T06:32:15.943' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (671, N'B27', N'', N'available', CAST(N'2026-04-01T06:32:21.003' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (672, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-01T06:32:25.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (673, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:32:29.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (674, N'B8', N'', N'available', CAST(N'2026-04-01T06:33:27.297' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (675, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:33:49.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (676, N'B8', N'', N'available', CAST(N'2026-04-01T06:34:06.163' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (677, N'B15', N'', N'available', CAST(N'2026-04-01T06:34:12.840' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (678, N'B8', N'', N'occupied', CAST(N'2026-04-01T06:34:23.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (679, N'B15', N'', N'occupied', CAST(N'2026-04-01T06:34:39.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (680, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:34:42.230' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (681, N'V2_Violation_2', N'SHR-1198', N'occupied', CAST(N'2026-04-01T06:35:00.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (682, N'B15', N'', N'available', CAST(N'2026-04-01T06:35:09.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (683, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-01T06:35:09.360' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (684, N'G6', N'', N'available', CAST(N'2026-04-01T06:35:10.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (685, N'B27', N'', N'occupied', CAST(N'2026-04-01T06:35:18.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (686, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-01T06:35:31.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (687, N'B15', N'', N'occupied', CAST(N'2026-04-01T06:35:34.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (688, N'B27', N'', N'available', CAST(N'2026-04-01T06:35:40.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (689, N'G6', N'', N'occupied', CAST(N'2026-04-01T06:35:50.870' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (690, N'B15', N'', N'available', CAST(N'2026-04-01T06:36:49.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (691, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T06:36:50.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (692, N'B9', N'', N'available', CAST(N'2026-04-01T06:36:50.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (693, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:37:30.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (694, N'B9', N'', N'occupied', CAST(N'2026-04-01T06:37:31.137' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (695, N'B15', N'', N'occupied', CAST(N'2026-04-01T06:37:32.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (696, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-01T06:37:35.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (697, N'B2', N'', N'available', CAST(N'2026-04-01T06:37:35.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (698, N'G6', N'', N'available', CAST(N'2026-04-01T06:37:50.700' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (699, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-01T06:37:57.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (700, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:38:00.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (701, N'B25', N'', N'available', CAST(N'2026-04-01T06:38:35.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (702, N'B8', N'', N'available', CAST(N'2026-04-01T06:38:38.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (703, N'B25', N'BGD-7593', N'occupied', CAST(N'2026-04-01T06:38:42.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (704, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:40:30.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (705, N'B2', N'BGD-7593', N'occupied', CAST(N'2026-04-01T06:40:45.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (706, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T06:40:59.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (707, N'B2', N'', N'available', CAST(N'2026-04-01T06:41:45.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (708, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T06:42:27.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (709, N'B14', N'', N'available', CAST(N'2026-04-01T06:42:47.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (710, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T06:43:03.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (711, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:43:13.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (712, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:43:32.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (714, N'G5', N'', N'occupied', CAST(N'2026-04-01T06:57:02.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (715, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:57:02.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (716, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:57:02.700' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (717, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T06:57:02.757' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (718, N'B9', N'', N'occupied', CAST(N'2026-04-01T06:57:02.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (719, N'B25', N'', N'occupied', CAST(N'2026-04-01T06:57:02.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (720, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:57:03.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (721, N'G6', N'', N'occupied', CAST(N'2026-04-01T06:57:03.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (722, N'B2', N'', N'occupied', CAST(N'2026-04-01T06:57:03.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (723, N'G2', N'', N'occupied', CAST(N'2026-04-01T06:57:03.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (724, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T06:57:04.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (726, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T06:59:03.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (727, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T06:59:03.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (728, N'B9', N'', N'occupied', CAST(N'2026-04-01T06:59:03.700' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (729, N'G2', N'', N'occupied', CAST(N'2026-04-01T06:59:04.517' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (730, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T06:59:06.213' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (731, N'B25', N'', N'occupied', CAST(N'2026-04-01T06:59:07.440' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (732, N'B14', N'', N'occupied', CAST(N'2026-04-01T06:59:07.617' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (733, N'B15', N'', N'occupied', CAST(N'2026-04-01T06:59:08.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (735, N'B2', N'', N'occupied', CAST(N'2026-04-01T07:02:05.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (736, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T07:02:05.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (737, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T07:02:05.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (738, N'B9', N'', N'occupied', CAST(N'2026-04-01T07:02:05.740' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (739, N'B25', N'', N'occupied', CAST(N'2026-04-01T07:02:05.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (740, N'B14', N'', N'occupied', CAST(N'2026-04-01T07:02:06.003' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (741, N'G6', N'', N'occupied', CAST(N'2026-04-01T07:02:06.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (742, N'G2', N'', N'occupied', CAST(N'2026-04-01T07:02:06.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (743, N'B15', N'', N'occupied', CAST(N'2026-04-01T07:02:16.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (744, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T07:02:19.160' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (745, N'B27', N'', N'occupied', CAST(N'2026-04-01T07:02:19.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (746, N'B15', N'', N'available', CAST(N'2026-04-01T07:02:36.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (747, N'B27', N'', N'available', CAST(N'2026-04-01T07:02:36.573' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (748, N'B27', N'', N'occupied', CAST(N'2026-04-01T07:02:45.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (749, N'B15', N'', N'occupied', CAST(N'2026-04-01T07:02:49.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (750, N'B18', N'', N'occupied', CAST(N'2026-04-01T07:02:51.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (751, N'G5', N'', N'occupied', CAST(N'2026-04-01T07:02:55.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (752, N'B2', N'', N'available', CAST(N'2026-04-01T07:02:56.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (753, N'B15', N'', N'available', CAST(N'2026-04-01T07:03:04.197' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (754, N'B27', N'', N'available', CAST(N'2026-04-01T07:03:04.200' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (755, N'B18', N'', N'available', CAST(N'2026-04-01T07:03:04.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (756, N'B27', N'', N'occupied', CAST(N'2026-04-01T07:03:16.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (757, N'B15', N'', N'occupied', CAST(N'2026-04-01T07:03:17.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (759, N'G5', N'', N'occupied', CAST(N'2026-04-01T07:04:20.360' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (760, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T07:04:20.417' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (761, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T07:04:20.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (762, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T07:04:20.543' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (763, N'B9', N'', N'occupied', CAST(N'2026-04-01T07:04:20.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (764, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T07:04:20.617' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (765, N'B25', N'', N'occupied', CAST(N'2026-04-01T07:04:20.717' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (766, N'B14', N'', N'occupied', CAST(N'2026-04-01T07:04:20.907' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (767, N'G6', N'', N'occupied', CAST(N'2026-04-01T07:04:21.007' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (768, N'B2', N'', N'occupied', CAST(N'2026-04-01T07:04:21.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (769, N'G2', N'', N'occupied', CAST(N'2026-04-01T07:04:21.540' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (770, N'B15', N'', N'occupied', CAST(N'2026-04-01T07:04:28.347' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (771, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T07:04:38.070' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (772, N'B15', N'', N'available', CAST(N'2026-04-01T07:04:40.227' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (773, N'B27', N'', N'occupied', CAST(N'2026-04-01T07:05:33.040' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (774, N'B27', N'', N'available', CAST(N'2026-04-01T07:05:54.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (775, N'B2', N'', N'available', CAST(N'2026-04-01T07:05:57.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (776, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T07:06:09.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (777, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T07:06:19.450' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (779, N'G2', N'', N'occupied', CAST(N'2026-04-01T07:10:12.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (780, N'G5', N'', N'occupied', CAST(N'2026-04-01T07:10:12.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (781, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T07:10:12.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (782, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T07:10:13.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (783, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T07:10:13.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (784, N'B9', N'', N'occupied', CAST(N'2026-04-01T07:10:13.157' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (785, N'B25', N'', N'occupied', CAST(N'2026-04-01T07:10:13.283' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (786, N'B21', N'', N'occupied', CAST(N'2026-04-01T07:10:13.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (787, N'B14', N'', N'occupied', CAST(N'2026-04-01T07:10:13.533' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (788, N'B2', N'', N'occupied', CAST(N'2026-04-01T07:10:13.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (789, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T07:10:34.937' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (790, N'B2', N'', N'available', CAST(N'2026-04-01T07:11:23.340' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (791, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T07:11:27.330' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (793, N'G5', N'', N'occupied', CAST(N'2026-04-01T12:53:29.813' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (794, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T12:53:29.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (795, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-01T12:53:29.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (796, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-01T12:53:29.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (798, N'B25', N'', N'occupied', CAST(N'2026-04-01T12:53:30.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (799, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T12:53:32.377' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (800, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-01T12:53:37.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (801, N'G6', N'', N'occupied', CAST(N'2026-04-01T12:54:02.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (802, N'B13_COO', N'', N'occupied', CAST(N'2026-04-01T12:54:13.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (803, N'G6', N'', N'available', CAST(N'2026-04-01T12:54:15.670' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (804, N'B8', N'', N'occupied', CAST(N'2026-04-01T12:54:15.723' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (805, N'B13_COO', N'', N'available', CAST(N'2026-04-01T12:54:33.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (806, N'G6', N'', N'occupied', CAST(N'2026-04-01T12:54:48.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (807, N'B6_Reserved', N'', N'available', CAST(N'2026-04-01T12:55:05.053' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (808, N'B8', N'', N'available', CAST(N'2026-04-01T12:55:09.337' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (809, N'B11_CFO', N'', N'available', CAST(N'2026-04-01T12:55:12.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (811, N'B10_CTO', N'', N'available', CAST(N'2026-04-01T12:55:13.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (812, N'G6', N'', N'available', CAST(N'2026-04-01T12:55:15.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (813, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-01T12:55:20.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (814, N'G6', N'', N'occupied', CAST(N'2026-04-01T12:55:20.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (815, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-01T12:55:21.543' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (816, N'B1_CRO', N'', N'available', CAST(N'2026-04-01T12:55:27.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (818, N'G6', N'', N'available', CAST(N'2026-04-01T12:55:44.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (819, N'G6', N'', N'occupied', CAST(N'2026-04-01T12:56:09.693' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1715, N'B12', N'', N'occupied', CAST(N'2026-04-02T06:27:36.490' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1716, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T06:27:36.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1717, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-02T06:27:36.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1718, N'B9', N'', N'occupied', CAST(N'2026-04-02T06:27:36.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1719, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T06:27:36.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1720, N'B15', N'', N'occupied', CAST(N'2026-04-02T06:27:36.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1721, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:27:38.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1722, N'G6', N'', N'occupied', CAST(N'2026-04-02T06:27:43.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1723, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:27:45.847' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1724, N'G5', N'', N'occupied', CAST(N'2026-04-02T06:27:46.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1725, N'B25', N'', N'occupied', CAST(N'2026-04-02T06:27:47.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1726, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:27:47.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1727, N'G6', N'', N'available', CAST(N'2026-04-02T06:28:04.003' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1728, N'B12', N'', N'available', CAST(N'2026-04-02T06:28:19.030' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1729, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T06:28:19.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1730, N'B27', N'', N'available', CAST(N'2026-04-02T06:28:20.927' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1731, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T06:28:27.437' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1732, N'G6', N'', N'occupied', CAST(N'2026-04-02T06:28:28.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1733, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:28:44.423' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1734, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:28:45.140' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1735, N'G2', N'', N'occupied', CAST(N'2026-04-02T06:28:45.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1736, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:28:50.530' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1737, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T06:29:07.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1738, N'G4', N'', N'occupied', CAST(N'2026-04-02T06:29:08.017' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1739, N'B12', N'', N'occupied', CAST(N'2026-04-02T06:29:08.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1740, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T06:29:09.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1741, N'B19', N'', N'available', CAST(N'2026-04-02T06:29:09.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1742, N'B12', N'', N'available', CAST(N'2026-04-02T06:30:13.713' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1743, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:31:48.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1744, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:31:48.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1745, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T06:31:51.280' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1746, N'B17', N'', N'available', CAST(N'2026-04-02T06:34:00.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1747, N'B19', N'', N'available', CAST(N'2026-04-02T06:34:00.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1748, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:34:30.567' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1749, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:34:30.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1750, N'B27', N'', N'available', CAST(N'2026-04-02T06:34:33.673' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1751, N'G4', N'', N'available', CAST(N'2026-04-02T06:34:53.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1752, N'G6', N'', N'available', CAST(N'2026-04-02T06:34:55.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1753, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:35:40.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1754, N'B17', N'', N'available', CAST(N'2026-04-02T06:36:02.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1755, N'B19', N'', N'available', CAST(N'2026-04-02T06:36:02.543' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1756, N'B15', N'', N'available', CAST(N'2026-04-02T06:36:08.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1757, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:36:15.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1758, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:36:15.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1759, N'B15', N'', N'occupied', CAST(N'2026-04-02T06:36:23.070' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1760, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T06:36:31.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1761, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:36:50.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1762, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T06:37:23.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1763, N'B17', N'', N'available', CAST(N'2026-04-02T06:38:32.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1764, N'B19', N'', N'available', CAST(N'2026-04-02T06:38:32.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1765, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:38:36.610' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1766, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T06:38:48.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1767, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:38:52.397' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1768, N'B27', N'', N'available', CAST(N'2026-04-02T06:38:53.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1769, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:38:54.727' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1770, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-02T06:38:55.543' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1771, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:38:56.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1772, N'B25', N'', N'available', CAST(N'2026-04-02T06:38:57.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1773, N'B25', N'', N'occupied', CAST(N'2026-04-02T06:39:08.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1774, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:39:09.137' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1775, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-02T06:39:10.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1776, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T06:39:11.030' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1777, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:39:20.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1778, N'G6', N'', N'occupied', CAST(N'2026-04-02T06:39:52.850' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1779, N'G5', N'', N'available', CAST(N'2026-04-02T06:40:59.943' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1780, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-02T06:41:17.533' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1781, N'B24', N'', N'available', CAST(N'2026-04-02T06:41:29.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1783, N'G2', N'', N'occupied', CAST(N'2026-04-02T06:42:25.707' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1784, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-02T06:42:25.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1785, N'B9', N'', N'occupied', CAST(N'2026-04-02T06:42:25.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1786, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T06:42:25.977' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1787, N'B25', N'', N'occupied', CAST(N'2026-04-02T06:42:26.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1788, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:42:26.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1789, N'B15', N'', N'occupied', CAST(N'2026-04-02T06:42:26.203' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1790, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:42:27.057' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1791, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T06:42:32.350' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1792, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:42:32.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1793, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:42:33.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1794, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:42:33.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1795, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T06:43:13.857' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1796, N'B27', N'', N'available', CAST(N'2026-04-02T06:43:15.713' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1797, N'B19', N'', N'available', CAST(N'2026-04-02T06:43:17.707' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1798, N'B17', N'', N'available', CAST(N'2026-04-02T06:43:19.297' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1799, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:43:23.383' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1800, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:43:37.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1801, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:43:37.427' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1802, N'B17', N'', N'available', CAST(N'2026-04-02T06:44:07.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1803, N'B19', N'', N'available', CAST(N'2026-04-02T06:44:07.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1804, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:44:35.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1805, N'B19', N'', N'occupied', CAST(N'2026-04-02T06:44:35.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1806, N'B13_COO', N'', N'available', CAST(N'2026-04-02T06:44:47.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1807, N'B21', N'', N'occupied', CAST(N'2026-04-02T06:45:05.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1808, N'B21', N'', N'available', CAST(N'2026-04-02T06:45:18.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1809, N'B21', N'', N'occupied', CAST(N'2026-04-02T06:45:48.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1811, N'G2', N'', N'occupied', CAST(N'2026-04-02T06:47:08.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1812, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-02T06:47:08.363' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1813, N'B9', N'', N'occupied', CAST(N'2026-04-02T06:47:08.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1814, N'B25', N'', N'occupied', CAST(N'2026-04-02T06:47:08.487' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1815, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:47:08.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1816, N'B15', N'', N'occupied', CAST(N'2026-04-02T06:47:08.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1817, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:47:10.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1818, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:47:11.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1819, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:47:11.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1820, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T06:47:11.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1821, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-02T06:47:12.657' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1822, N'B17', N'', N'available', CAST(N'2026-04-02T06:48:23.063' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1823, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:48:27.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1824, N'B21', N'', N'occupied', CAST(N'2026-04-02T06:48:42.710' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1825, N'B21', N'', N'available', CAST(N'2026-04-02T06:48:50.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1826, N'B1_CRO', N'', N'available', CAST(N'2026-04-02T06:48:52.847' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1827, N'B17', N'', N'available', CAST(N'2026-04-02T06:48:53.030' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1828, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:49:07.297' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1829, N'B17', N'', N'available', CAST(N'2026-04-02T06:50:00.543' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1830, N'B2', N'', N'available', CAST(N'2026-04-02T06:50:27.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1831, N'B3_CEO', N'', N'available', CAST(N'2026-04-02T06:50:27.747' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1832, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:50:32.343' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1834, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T06:50:37.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1836, N'G2', N'', N'occupied', CAST(N'2026-04-02T06:51:30.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1837, N'G4', N'', N'occupied', CAST(N'2026-04-02T06:51:30.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1838, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T06:51:31.050' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1839, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-02T06:51:31.100' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1840, N'B9', N'', N'occupied', CAST(N'2026-04-02T06:51:31.143' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1841, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T06:51:31.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1842, N'B25', N'', N'occupied', CAST(N'2026-04-02T06:51:31.230' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1843, N'B15', N'', N'occupied', CAST(N'2026-04-02T06:51:31.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1844, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:51:31.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1845, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:51:31.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1846, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:51:39.457' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1847, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:51:40.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1848, N'B2', N'', N'available', CAST(N'2026-04-02T06:52:03.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1849, N'B3_CEO', N'', N'available', CAST(N'2026-04-02T06:52:04.147' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1850, N'B21', N'', N'occupied', CAST(N'2026-04-02T06:52:15.080' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1851, N'B21', N'', N'available', CAST(N'2026-04-02T06:52:36.063' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1852, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:52:50.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1853, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T06:52:50.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1854, N'B24', N'', N'available', CAST(N'2026-04-02T06:53:08.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1855, N'B17', N'', N'available', CAST(N'2026-04-02T06:53:11.747' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1856, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:53:18.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1857, N'B2', N'', N'available', CAST(N'2026-04-02T06:53:28.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1858, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:53:32.853' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1859, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:53:33.907' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1860, N'B24', N'', N'available', CAST(N'2026-04-02T06:53:40.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1861, N'B17', N'', N'available', CAST(N'2026-04-02T06:53:41.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1862, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:53:56.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1863, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:53:57.717' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1864, N'B17', N'', N'available', CAST(N'2026-04-02T06:54:41.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1865, N'B12', N'', N'occupied', CAST(N'2026-04-02T06:54:44.693' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1866, N'B2', N'', N'available', CAST(N'2026-04-02T06:54:59.377' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1867, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:55:07.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1868, N'B12', N'', N'available', CAST(N'2026-04-02T06:55:09.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1869, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:55:16.817' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1870, N'G6', N'', N'occupied', CAST(N'2026-04-02T06:55:32.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1871, N'B27', N'', N'available', CAST(N'2026-04-02T06:55:35.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1872, N'B27', N'', N'occupied', CAST(N'2026-04-02T06:55:40.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1873, N'B2', N'', N'available', CAST(N'2026-04-02T06:55:55.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1874, N'B12', N'', N'occupied', CAST(N'2026-04-02T06:56:52.037' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1875, N'B24', N'', N'available', CAST(N'2026-04-02T06:57:10.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1876, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:57:18.250' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1877, N'B21', N'', N'occupied', CAST(N'2026-04-02T06:57:18.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1878, N'B12', N'', N'available', CAST(N'2026-04-02T06:57:22.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1879, N'B17', N'', N'available', CAST(N'2026-04-02T06:57:24.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1880, N'B24', N'', N'available', CAST(N'2026-04-02T06:57:26.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1881, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:57:31.193' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1882, N'B24', N'', N'occupied', CAST(N'2026-04-02T06:57:34.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1883, N'B21', N'', N'available', CAST(N'2026-04-02T06:57:42.683' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1884, N'B2', N'', N'available', CAST(N'2026-04-02T06:57:43.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1885, N'B12', N'', N'occupied', CAST(N'2026-04-02T06:57:46.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1886, N'B17', N'', N'occupied', CAST(N'2026-04-02T06:57:54.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1887, N'B2', N'', N'occupied', CAST(N'2026-04-02T06:58:23.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1888, N'B21', N'', N'occupied', CAST(N'2026-04-02T06:58:52.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1889, N'B2', N'', N'available', CAST(N'2026-04-02T06:58:57.490' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1890, N'B21', N'', N'available', CAST(N'2026-04-02T06:59:00.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1891, N'B21', N'', N'occupied', CAST(N'2026-04-02T07:02:28.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1892, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:02:34.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1893, N'B21', N'', N'available', CAST(N'2026-04-02T07:02:36.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1894, N'B27', N'', N'available', CAST(N'2026-04-02T07:02:43.150' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1895, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T07:02:51.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1896, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-02T07:02:53.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1897, N'B25', N'', N'available', CAST(N'2026-04-02T07:02:56.177' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1898, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T07:03:00.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1899, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:03:01.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1900, N'B12', N'', N'available', CAST(N'2026-04-02T07:03:09.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1901, N'B2', N'', N'available', CAST(N'2026-04-02T07:03:20.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1902, N'B12', N'', N'occupied', CAST(N'2026-04-02T07:03:41.670' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1903, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T07:03:41.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1904, N'B25', N'', N'occupied', CAST(N'2026-04-02T07:03:41.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1905, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-02T07:03:43.373' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1906, N'B17', N'', N'available', CAST(N'2026-04-02T07:03:44.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1907, N'B17', N'', N'occupied', CAST(N'2026-04-02T07:03:51.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1908, N'B12', N'', N'available', CAST(N'2026-04-02T07:03:55.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1909, N'B12', N'', N'occupied', CAST(N'2026-04-02T07:04:39.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1910, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-02T07:05:12.060' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1911, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T07:05:14.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1912, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:05:18.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1913, N'B13_COO', N'', N'available', CAST(N'2026-04-02T07:05:20.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1914, N'B25', N'', N'available', CAST(N'2026-04-02T07:05:21.863' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1915, N'B8', N'', N'available', CAST(N'2026-04-02T07:05:22.507' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1916, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T07:05:33.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1917, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-02T07:05:35.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1918, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T07:05:40.043' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1919, N'G5', N'', N'occupied', CAST(N'2026-04-02T07:05:52.483' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1920, N'G4', N'', N'available', CAST(N'2026-04-02T07:05:54.773' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1921, N'B25', N'', N'occupied', CAST(N'2026-04-02T07:06:02.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1922, N'G4', N'', N'occupied', CAST(N'2026-04-02T07:06:08.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1923, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:06:13.667' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1924, N'B8', N'', N'available', CAST(N'2026-04-02T07:06:42.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1925, N'B27', N'', N'occupied', CAST(N'2026-04-02T07:07:15.887' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1926, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T07:07:16.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1927, N'B2', N'', N'available', CAST(N'2026-04-02T07:07:17.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1928, N'B21', N'', N'occupied', CAST(N'2026-04-02T07:07:40.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1929, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:07:47.887' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1930, N'B17', N'', N'available', CAST(N'2026-04-02T07:07:49.297' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1931, N'B2', N'', N'available', CAST(N'2026-04-02T07:07:58.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1932, N'B21', N'', N'available', CAST(N'2026-04-02T07:08:01.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1933, N'B17', N'', N'occupied', CAST(N'2026-04-02T07:08:38.063' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1934, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:09:05.570' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1935, N'B8', N'', N'available', CAST(N'2026-04-02T07:09:18.377' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1936, N'B24', N'', N'available', CAST(N'2026-04-02T07:09:41.270' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1937, N'B24', N'', N'occupied', CAST(N'2026-04-02T07:09:52.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1938, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:10:12.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1939, N'B8', N'', N'available', CAST(N'2026-04-02T07:10:34.670' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1940, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:10:51.193' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1941, N'B2', N'', N'available', CAST(N'2026-04-02T07:11:00.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1942, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:11:05.417' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1943, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:11:07.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1944, N'B8', N'', N'available', CAST(N'2026-04-02T07:11:14.803' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1945, N'B24', N'', N'available', CAST(N'2026-04-02T07:11:15.897' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1946, N'G5', N'', N'available', CAST(N'2026-04-02T07:11:27.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1947, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-02T07:11:27.483' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1948, N'B24', N'', N'occupied', CAST(N'2026-04-02T07:11:36.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1949, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:11:37.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1950, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-02T07:11:39.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1951, N'B2', N'', N'available', CAST(N'2026-04-02T07:11:48.030' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1952, N'B8', N'', N'available', CAST(N'2026-04-02T07:12:50.047' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1953, N'B17', N'', N'available', CAST(N'2026-04-02T07:13:30.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1954, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:13:37.187' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1955, N'B27', N'', N'available', CAST(N'2026-04-02T07:13:39.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1956, N'B17', N'', N'occupied', CAST(N'2026-04-02T07:13:41.773' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1957, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T07:13:55.847' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1958, N'B2', N'', N'available', CAST(N'2026-04-02T07:13:56.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1959, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T07:14:03.507' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1960, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T07:14:10.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1961, N'G6', N'', N'available', CAST(N'2026-04-02T07:14:13.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1962, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T07:14:29.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1963, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:14:29.577' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1964, N'B17', N'', N'available', CAST(N'2026-04-02T07:14:41.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1965, N'G6', N'', N'occupied', CAST(N'2026-04-02T07:14:45.783' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1966, N'G6', N'', N'available', CAST(N'2026-04-02T07:14:54.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1967, N'V2_Violation_2', N'', N'occupied', CAST(N'2026-04-02T07:14:54.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1968, N'B14', N'', N'occupied', CAST(N'2026-04-02T07:14:57.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1969, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T07:15:01.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1970, N'B17', N'', N'occupied', CAST(N'2026-04-02T07:15:08.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1971, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:15:23.807' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1972, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T07:15:53.513' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1973, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T07:16:01.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1974, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T07:16:12.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1975, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T07:16:13.167' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1976, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-02T07:16:36.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1977, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T07:16:39.060' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1978, N'B2', N'', N'available', CAST(N'2026-04-02T07:18:22.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1979, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:19:16.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1980, N'B12', N'', N'available', CAST(N'2026-04-02T07:19:42.617' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1981, N'B12', N'', N'occupied', CAST(N'2026-04-02T07:19:51.647' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1982, N'B13_COO', N'', N'available', CAST(N'2026-04-02T07:19:53.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1983, N'B8', N'', N'available', CAST(N'2026-04-02T07:20:09.963' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1985, N'G2', N'', N'occupied', CAST(N'2026-04-02T07:21:13.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1986, N'G4', N'', N'occupied', CAST(N'2026-04-02T07:21:13.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1987, N'B12', N'', N'occupied', CAST(N'2026-04-02T07:21:13.963' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1988, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-02T07:21:14.043' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1989, N'B9', N'', N'occupied', CAST(N'2026-04-02T07:21:14.087' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1990, N'B17', N'', N'occupied', CAST(N'2026-04-02T07:21:14.193' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1991, N'B14', N'', N'occupied', CAST(N'2026-04-02T07:21:14.293' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1992, N'B24', N'', N'occupied', CAST(N'2026-04-02T07:21:14.993' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1993, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T07:21:16.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1994, N'B15', N'', N'occupied', CAST(N'2026-04-02T07:21:17.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1995, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:21:19.330' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1996, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T07:21:21.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1997, N'B25', N'', N'occupied', CAST(N'2026-04-02T07:21:50.520' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1998, N'B21', N'', N'occupied', CAST(N'2026-04-02T07:21:54.803' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (1999, N'B27', N'', N'occupied', CAST(N'2026-04-02T07:21:54.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2000, N'B2', N'', N'available', CAST(N'2026-04-02T07:22:02.473' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2001, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:22:13.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2002, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:22:19.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2003, N'B8', N'', N'available', CAST(N'2026-04-02T07:22:30.617' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2004, N'B21', N'', N'available', CAST(N'2026-04-02T07:22:49.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2005, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:23:03.843' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2006, N'B8', N'', N'available', CAST(N'2026-04-02T07:23:21.143' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2007, N'B2', N'', N'available', CAST(N'2026-04-02T07:23:40.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2008, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:23:50.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2009, N'B2', N'', N'available', CAST(N'2026-04-02T07:24:40.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2010, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:25:05.347' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2011, N'B27', N'', N'available', CAST(N'2026-04-02T07:25:12.160' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2012, N'B27', N'', N'occupied', CAST(N'2026-04-02T07:25:17.817' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2013, N'B11_CFO', N'', N'available', CAST(N'2026-04-02T07:25:20.423' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2014, N'B25', N'', N'available', CAST(N'2026-04-02T07:25:23.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2015, N'B25', N'', N'occupied', CAST(N'2026-04-02T07:25:36.123' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2016, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T07:25:44.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2017, N'B2', N'', N'available', CAST(N'2026-04-02T07:27:05.080' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2018, N'B9', N'', N'available', CAST(N'2026-04-02T07:27:05.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2019, N'B9', N'', N'occupied', CAST(N'2026-04-02T07:27:10.897' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2020, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:27:12.460' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2021, N'B27', N'', N'available', CAST(N'2026-04-02T07:27:20.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2022, N'B27', N'', N'occupied', CAST(N'2026-04-02T07:28:06.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2023, N'G6', N'', N'occupied', CAST(N'2026-04-02T07:28:24.707' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2024, N'B27', N'', N'available', CAST(N'2026-04-02T07:28:25.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2025, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T07:28:26.610' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2026, N'B8', N'', N'occupied', CAST(N'2026-04-02T07:28:50.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2027, N'B2', N'', N'available', CAST(N'2026-04-02T07:29:13.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2028, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:29:27.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2029, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-02T07:29:53.750' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2030, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-02T07:30:13.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2031, N'B21', N'', N'occupied', CAST(N'2026-04-02T07:30:15.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2032, N'B21', N'', N'available', CAST(N'2026-04-02T07:30:32.313' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2033, N'B2', N'', N'available', CAST(N'2026-04-02T07:30:55.327' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2034, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:31:05.857' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2035, N'B2', N'', N'available', CAST(N'2026-04-02T07:31:22.337' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2036, N'B21', N'', N'occupied', CAST(N'2026-04-02T07:41:05.717' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2037, N'B27', N'', N'occupied', CAST(N'2026-04-02T07:41:10.060' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2038, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:41:13.737' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2039, N'B13_COO', N'', N'available', CAST(N'2026-04-02T07:41:26.197' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2040, N'B8', N'', N'available', CAST(N'2026-04-02T07:41:28.143' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2041, N'B2', N'', N'available', CAST(N'2026-04-02T07:41:36.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2042, N'B21', N'', N'available', CAST(N'2026-04-02T07:42:33.823' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2043, N'B21', N'', N'occupied', CAST(N'2026-04-02T07:42:55.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2044, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:43:25.820' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2045, N'B2', N'', N'available', CAST(N'2026-04-02T07:43:52.330' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2046, N'B2', N'', N'occupied', CAST(N'2026-04-02T07:44:05.593' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2047, N'B21', N'', N'available', CAST(N'2026-04-02T07:44:09.293' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2049, N'B8', N'', N'occupied', CAST(N'2026-04-02T08:39:36.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2050, N'B12', N'', N'occupied', CAST(N'2026-04-02T08:39:36.330' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2051, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-02T08:39:36.337' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2052, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-02T08:39:36.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2053, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-02T08:39:36.427' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2054, N'B9', N'', N'occupied', CAST(N'2026-04-02T08:39:36.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2055, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-02T08:39:36.473' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2056, N'B25', N'', N'occupied', CAST(N'2026-04-02T08:39:36.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2057, N'B17', N'', N'occupied', CAST(N'2026-04-02T08:39:36.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2058, N'B15', N'', N'occupied', CAST(N'2026-04-02T08:39:36.713' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2059, N'G6', N'', N'occupied', CAST(N'2026-04-02T08:39:36.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2060, N'B2', N'', N'occupied', CAST(N'2026-04-02T08:39:36.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2061, N'B24', N'', N'occupied', CAST(N'2026-04-02T08:39:37.420' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2062, N'G5', N'', N'occupied', CAST(N'2026-04-02T08:39:39.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2063, N'G2', N'', N'occupied', CAST(N'2026-04-02T08:39:39.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2064, N'B27', N'', N'occupied', CAST(N'2026-04-02T08:39:40.737' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2065, N'B14', N'', N'occupied', CAST(N'2026-04-02T08:39:41.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2067, N'B27', N'', N'available', CAST(N'2026-04-02T08:40:00.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2068, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T08:40:01.647' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2069, N'B2', N'', N'available', CAST(N'2026-04-02T08:40:14.267' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2070, N'B2', N'', N'occupied', CAST(N'2026-04-02T08:40:34.990' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2071, N'B13_COO', N'', N'available', CAST(N'2026-04-02T08:41:10.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2072, N'B2', N'', N'available', CAST(N'2026-04-02T08:42:02.813' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2073, N'B15', N'', N'available', CAST(N'2026-04-02T08:42:03.107' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2074, N'B2', N'', N'occupied', CAST(N'2026-04-02T08:43:05.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2075, N'B15', N'', N'occupied', CAST(N'2026-04-02T08:43:27.237' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2076, N'B13_COO', N'', N'occupied', CAST(N'2026-04-02T08:43:42.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2077, N'B13_COO', N'', N'available', CAST(N'2026-04-02T08:44:17.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (2078, N'B2', N'', N'available', CAST(N'2026-04-02T08:44:21.863' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3018, N'G2', N'', N'occupied', CAST(N'2026-04-11T11:57:15.160' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3019, N'B2', N'', N'occupied', CAST(N'2026-04-11T11:57:15.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3020, N'G2', N'', N'occupied', CAST(N'2026-04-11T12:00:10.817' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3021, N'B2', N'', N'occupied', CAST(N'2026-04-11T12:00:11.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3022, N'G2', N'', N'occupied', CAST(N'2026-04-11T12:01:26.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3023, N'B2', N'', N'occupied', CAST(N'2026-04-11T12:01:27.003' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3024, N'G3', N'', N'available', CAST(N'2026-04-11T12:08:57.937' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3025, N'G4', N'', N'available', CAST(N'2026-04-11T12:08:58.043' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3026, N'G5', N'', N'available', CAST(N'2026-04-11T12:08:58.070' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3027, N'G6', N'', N'available', CAST(N'2026-04-11T12:08:58.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3028, N'B8', N'', N'available', CAST(N'2026-04-11T12:08:58.167' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3029, N'B12', N'', N'available', CAST(N'2026-04-11T12:08:58.187' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3030, N'B10_CTO', N'', N'available', CAST(N'2026-04-11T12:08:58.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3031, N'B3_CEO', N'', N'available', CAST(N'2026-04-11T12:08:58.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3032, N'B6_Reserved', N'', N'available', CAST(N'2026-04-11T12:08:58.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3033, N'B9', N'', N'available', CAST(N'2026-04-11T12:08:58.420' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3034, N'B11_CFO', N'', N'available', CAST(N'2026-04-11T12:08:58.437' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3035, N'B25', N'', N'available', CAST(N'2026-04-11T12:08:58.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3036, N'B24', N'', N'available', CAST(N'2026-04-11T12:08:58.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3037, N'B17', N'', N'available', CAST(N'2026-04-11T12:08:58.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3038, N'B19', N'', N'available', CAST(N'2026-04-11T12:08:58.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3039, N'B20', N'', N'available', CAST(N'2026-04-11T12:08:58.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3040, N'B23', N'', N'available', CAST(N'2026-04-11T12:08:58.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3041, N'B22', N'', N'available', CAST(N'2026-04-11T12:08:58.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3042, N'B15', N'', N'available', CAST(N'2026-04-11T12:08:58.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3043, N'B14', N'', N'available', CAST(N'2026-04-11T12:08:58.903' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3044, N'V1_Violation_1', NULL, N'occupied', CAST(N'2026-04-11T12:52:19.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3045, N'V2_Violation_2', NULL, N'occupied', CAST(N'2026-04-11T12:52:19.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3046, N'G2', NULL, N'available', CAST(N'2026-04-11T12:53:48.833' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3047, N'G2', NULL, N'occupied', CAST(N'2026-04-11T12:54:05.833' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3048, N'G2', N'', N'available', CAST(N'2026-04-11T12:57:05.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3049, N'G1', N'', N'occupied', CAST(N'2026-04-12T10:53:01.667' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3050, N'G5', N'', N'occupied', CAST(N'2026-04-12T10:53:01.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3051, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-12T10:53:01.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3052, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-12T10:53:01.820' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3053, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-12T10:53:01.883' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3054, N'B9', N'', N'occupied', CAST(N'2026-04-12T10:53:01.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3055, N'GMIA', N'', N'occupied', CAST(N'2026-04-12T10:53:01.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3056, N'B20', N'', N'occupied', CAST(N'2026-04-12T10:53:02.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3057, N'B23', N'', N'occupied', CAST(N'2026-04-12T10:53:02.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3058, N'B15', N'', N'occupied', CAST(N'2026-04-12T10:53:02.147' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3059, N'G6', N'', N'occupied', CAST(N'2026-04-12T10:53:02.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3060, N'G2', N'', N'occupied', CAST(N'2026-04-12T10:53:02.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3061, N'B24', N'', N'occupied', CAST(N'2026-04-12T10:53:05.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3062, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-12T10:53:13.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3063, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-12T10:53:13.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3064, N'B22', N'', N'occupied', CAST(N'2026-04-12T10:53:23.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3065, N'G3', N'', N'occupied', CAST(N'2026-04-12T10:54:39.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3066, N'G3', N'', N'available', CAST(N'2026-04-12T10:55:03.817' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3067, N'G6', N'', N'available', CAST(N'2026-04-12T10:55:15.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3068, N'B2', N'', N'available', CAST(N'2026-04-12T10:55:15.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3069, N'G3', N'', N'occupied', CAST(N'2026-04-12T10:55:31.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3070, N'G6', N'', N'occupied', CAST(N'2026-04-12T12:22:11.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3071, N'G3', N'', N'available', CAST(N'2026-04-12T12:22:25.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3072, N'B6_Reserved', N'', N'available', CAST(N'2026-04-12T12:22:25.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3073, N'B15', N'', N'available', CAST(N'2026-04-12T12:22:26.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3074, N'G4', N'', N'occupied', CAST(N'2026-04-12T12:22:28.050' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3075, N'B14', N'', N'occupied', CAST(N'2026-04-12T12:22:39.247' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3076, N'G6', N'', N'available', CAST(N'2026-04-12T12:23:10.000' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3077, N'B12', N'', N'occupied', CAST(N'2026-04-12T12:23:12.203' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3078, N'B25', N'', N'occupied', CAST(N'2026-04-12T12:23:20.043' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3079, N'G4', N'', N'available', CAST(N'2026-04-12T12:23:21.497' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3080, N'B2', N'', N'occupied', CAST(N'2026-04-12T12:23:40.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3081, N'B13_COO', N'', N'occupied', CAST(N'2026-04-12T12:23:40.693' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3082, N'B24', N'', N'available', CAST(N'2026-04-12T12:23:51.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3083, N'B25', N'', N'available', CAST(N'2026-04-12T12:23:54.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3084, N'B14', N'', N'available', CAST(N'2026-04-12T12:23:59.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3085, N'B9', N'', N'available', CAST(N'2026-04-12T12:24:02.013' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3086, N'G6', N'', N'occupied', CAST(N'2026-04-12T12:24:05.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3087, N'B2', N'', N'available', CAST(N'2026-04-12T12:24:25.213' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3088, N'B14', N'', N'occupied', CAST(N'2026-04-12T12:24:31.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3089, N'B10_CTO', N'', N'available', CAST(N'2026-04-12T12:24:43.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3090, N'G6', N'', N'available', CAST(N'2026-04-12T12:25:13.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3091, N'G4', N'', N'occupied', CAST(N'2026-04-12T12:25:34.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3092, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-12T12:25:40.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3093, N'G1', N'', N'available', CAST(N'2026-04-12T16:32:12.870' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3094, N'G2', N'', N'available', CAST(N'2026-04-12T16:32:12.893' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3095, N'G4', N'', N'available', CAST(N'2026-04-12T16:32:12.937' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3096, N'G5', N'', N'available', CAST(N'2026-04-12T16:32:12.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3097, N'B12', N'', N'available', CAST(N'2026-04-12T16:32:12.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3098, N'B3_CEO', N'', N'available', CAST(N'2026-04-12T16:32:13.057' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3099, N'B11_CFO', N'', N'available', CAST(N'2026-04-12T16:32:13.140' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3100, N'B13_COO', N'', N'available', CAST(N'2026-04-12T16:32:13.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3101, N'GMIA', N'', N'available', CAST(N'2026-04-12T16:32:13.193' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3102, N'B20', N'', N'available', CAST(N'2026-04-12T16:32:13.267' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3103, N'B23', N'', N'available', CAST(N'2026-04-12T16:32:13.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3104, N'B22', N'', N'available', CAST(N'2026-04-12T16:32:13.350' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3105, N'B14', N'', N'available', CAST(N'2026-04-12T16:32:13.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3106, N'G1', N'', N'occupied', CAST(N'2026-04-13T05:30:16.763' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3107, N'G5', N'', N'occupied', CAST(N'2026-04-13T05:30:16.840' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3108, N'B2', N'', N'occupied', CAST(N'2026-04-13T05:30:16.943' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3109, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-13T05:30:16.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3110, N'B9', N'', N'occupied', CAST(N'2026-04-13T05:30:17.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3111, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-13T05:30:17.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3112, N'B15', N'', N'occupied', CAST(N'2026-04-13T05:30:17.383' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3113, N'B27', N'', N'occupied', CAST(N'2026-04-13T05:30:18.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3114, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:30:18.090' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3115, N'B12', N'', N'occupied', CAST(N'2026-04-13T05:30:33.120' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3116, N'B2', N'', N'available', CAST(N'2026-04-13T05:31:23.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3117, N'B2', N'', N'occupied', CAST(N'2026-04-13T05:31:30.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3118, N'G6', N'', N'occupied', CAST(N'2026-04-13T05:31:45.140' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3119, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-13T05:32:10.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3120, N'GMIA', N'', N'occupied', CAST(N'2026-04-13T05:32:25.327' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3121, N'G6', N'', N'available', CAST(N'2026-04-13T05:32:33.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3122, N'GMIA', N'', N'available', CAST(N'2026-04-13T05:32:46.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3123, N'B6_Reserved', N'', N'available', CAST(N'2026-04-13T05:34:52.387' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3124, N'B11_CFO', N'', N'available', CAST(N'2026-04-13T05:35:00.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3125, N'B9', N'', N'available', CAST(N'2026-04-13T05:35:02.883' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3126, N'B9', N'', N'occupied', CAST(N'2026-04-13T05:35:08.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3127, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-13T05:35:08.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3128, N'G6', N'', N'occupied', CAST(N'2026-04-13T05:35:14.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3129, N'B8', N'', N'occupied', CAST(N'2026-04-13T05:35:18.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3130, N'B25', N'', N'occupied', CAST(N'2026-04-13T05:35:37.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3131, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-13T05:35:39.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3132, N'G6', N'', N'available', CAST(N'2026-04-13T05:35:50.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3133, N'B2', N'', N'available', CAST(N'2026-04-13T05:35:53.037' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3134, N'B8', N'', N'available', CAST(N'2026-04-13T05:36:33.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3135, N'B2', N'', N'occupied', CAST(N'2026-04-13T05:37:20.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3136, N'B3_CEO', N'', N'available', CAST(N'2026-04-13T05:37:36.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3137, N'B8', N'', N'occupied', CAST(N'2026-04-13T05:44:13.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3138, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-13T05:44:46.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3139, N'G6', N'', N'occupied', CAST(N'2026-04-13T05:44:47.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3140, N'G6', N'', N'available', CAST(N'2026-04-13T05:45:43.910' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3141, N'B21', N'', N'occupied', CAST(N'2026-04-13T05:45:51.610' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3142, N'G6', N'', N'occupied', CAST(N'2026-04-13T05:45:53.473' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3143, N'B27', N'', N'available', CAST(N'2026-04-13T05:46:08.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3144, N'B11_CFO', N'', N'available', CAST(N'2026-04-13T05:46:31.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3145, N'B21', N'', N'available', CAST(N'2026-04-13T05:46:33.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3146, N'B3_CEO', N'', N'available', CAST(N'2026-04-13T05:46:39.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3147, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-13T05:47:40.247' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3148, N'B27', N'', N'occupied', CAST(N'2026-04-13T05:48:16.130' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3149, N'B21', N'', N'occupied', CAST(N'2026-04-13T05:48:19.097' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3150, N'B2', N'', N'available', CAST(N'2026-04-13T05:48:43.440' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3151, N'B2', N'', N'occupied', CAST(N'2026-04-13T05:50:40.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3152, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-13T05:50:40.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3153, N'B8', N'', N'available', CAST(N'2026-04-13T05:50:49.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3154, N'B11_CFO', N'', N'available', CAST(N'2026-04-13T05:50:55.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3155, N'G6', N'', N'available', CAST(N'2026-04-13T05:50:56.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3156, N'G6', N'', N'occupied', CAST(N'2026-04-13T05:51:05.713' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3157, N'G4', N'', N'occupied', CAST(N'2026-04-13T05:51:06.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3158, N'B8', N'', N'occupied', CAST(N'2026-04-13T05:51:08.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3159, N'B27', N'', N'available', CAST(N'2026-04-13T05:51:08.847' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3160, N'B16', N'', N'occupied', CAST(N'2026-04-13T05:51:14.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3161, N'B20', N'', N'occupied', CAST(N'2026-04-13T05:51:15.113' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3162, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-13T05:51:17.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3163, N'B23', N'', N'occupied', CAST(N'2026-04-13T05:51:22.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3164, N'B16', N'', N'available', CAST(N'2026-04-13T05:51:24.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3165, N'B27', N'', N'occupied', CAST(N'2026-04-13T05:51:26.033' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3166, N'B20', N'', N'available', CAST(N'2026-04-13T05:51:26.773' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3167, N'G4', N'', N'available', CAST(N'2026-04-13T05:51:35.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3168, N'B16', N'', N'occupied', CAST(N'2026-04-13T05:51:35.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3169, N'B23', N'', N'available', CAST(N'2026-04-13T05:51:38.757' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3170, N'B20', N'', N'occupied', CAST(N'2026-04-13T05:51:40.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3171, N'B24', N'', N'occupied', CAST(N'2026-04-13T05:51:43.143' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3172, N'B21', N'', N'available', CAST(N'2026-04-13T05:51:43.453' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3173, N'B16', N'', N'available', CAST(N'2026-04-13T05:51:48.703' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3174, N'B22', N'', N'occupied', CAST(N'2026-04-13T05:51:50.420' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3175, N'G3', N'', N'occupied', CAST(N'2026-04-13T05:51:50.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3176, N'G6', N'', N'available', CAST(N'2026-04-13T05:51:50.507' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3177, N'B20', N'', N'available', CAST(N'2026-04-13T05:51:52.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3178, N'G6', N'', N'occupied', CAST(N'2026-04-13T05:51:53.623' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3179, N'B24', N'', N'available', CAST(N'2026-04-13T05:51:57.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3180, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-13T05:52:03.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3181, N'G2', N'', N'available', CAST(N'2026-04-13T05:52:05.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3182, N'B24', N'', N'occupied', CAST(N'2026-04-13T05:52:15.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3183, N'B21', N'', N'occupied', CAST(N'2026-04-13T05:52:20.100' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3184, N'B8', N'', N'available', CAST(N'2026-04-13T05:52:22.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3185, N'B11_CFO', N'', N'available', CAST(N'2026-04-13T05:52:22.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3186, N'B8', N'', N'occupied', CAST(N'2026-04-13T05:52:27.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3187, N'B21', N'', N'available', CAST(N'2026-04-13T05:52:29.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3188, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:52:53.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3189, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-13T05:52:54.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3190, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-13T05:53:12.137' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3191, N'G2', N'', N'available', CAST(N'2026-04-13T05:53:18.517' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3192, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:53:24.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3193, N'G2', N'', N'available', CAST(N'2026-04-13T05:53:38.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3194, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:53:51.283' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3195, N'G2', N'', N'available', CAST(N'2026-04-13T05:54:01.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3196, N'B1_CRO', N'', N'available', CAST(N'2026-04-13T05:54:12.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3197, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:54:49.000' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3198, N'G2', N'', N'available', CAST(N'2026-04-13T05:55:11.053' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3199, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:56:13.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3200, N'G2', N'', N'available', CAST(N'2026-04-13T05:56:49.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3201, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:57:03.907' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3202, N'G2', N'', N'available', CAST(N'2026-04-13T05:57:26.180' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3203, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-13T05:57:51.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3204, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-13T05:58:20.197' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3205, N'B8', N'', N'available', CAST(N'2026-04-13T05:58:42.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3206, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:58:46.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3207, N'B12', N'', N'available', CAST(N'2026-04-13T05:58:48.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3208, N'B27', N'', N'available', CAST(N'2026-04-13T05:58:58.453' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3209, N'G3', N'', N'available', CAST(N'2026-04-13T05:59:01.160' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3210, N'G4', N'', N'occupied', CAST(N'2026-04-13T05:59:01.700' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3211, N'B21', N'', N'occupied', CAST(N'2026-04-13T05:59:03.030' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3212, N'B20', N'', N'occupied', CAST(N'2026-04-13T05:59:10.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3213, N'B25', N'', N'available', CAST(N'2026-04-13T05:59:19.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3214, N'B12', N'', N'occupied', CAST(N'2026-04-13T05:59:30.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3215, N'B20', N'', N'available', CAST(N'2026-04-13T05:59:32.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3216, N'B8', N'', N'occupied', CAST(N'2026-04-13T05:59:32.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3217, N'B27', N'', N'occupied', CAST(N'2026-04-13T05:59:33.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3218, N'G4', N'', N'available', CAST(N'2026-04-13T05:59:40.237' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3219, N'G3', N'', N'occupied', CAST(N'2026-04-13T05:59:43.040' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3220, N'B25', N'', N'occupied', CAST(N'2026-04-13T05:59:46.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3221, N'G2', N'', N'available', CAST(N'2026-04-13T05:59:50.690' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3222, N'G6', N'', N'available', CAST(N'2026-04-13T05:59:51.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3223, N'B20', N'', N'occupied', CAST(N'2026-04-13T05:59:55.963' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3224, N'G2', N'', N'occupied', CAST(N'2026-04-13T05:59:56.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3225, N'G6', N'', N'occupied', CAST(N'2026-04-13T06:00:04.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3226, N'G3', N'', N'available', CAST(N'2026-04-13T06:00:14.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3227, N'B2', N'', N'available', CAST(N'2026-04-13T06:00:14.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3228, N'B21', N'', N'available', CAST(N'2026-04-13T06:00:17.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3229, N'B20', N'', N'available', CAST(N'2026-04-13T06:00:18.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3230, N'B2', N'', N'occupied', CAST(N'2026-04-13T06:02:20.147' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3231, N'G3', N'', N'occupied', CAST(N'2026-04-13T06:02:21.450' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3232, N'B11_CFO', N'', N'available', CAST(N'2026-04-13T06:02:26.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3233, N'G6', N'', N'available', CAST(N'2026-04-13T06:02:28.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3234, N'G2', N'', N'available', CAST(N'2026-04-13T06:02:29.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3235, N'B8', N'', N'available', CAST(N'2026-04-13T06:05:01.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3236, N'B12', N'', N'available', CAST(N'2026-04-13T06:05:14.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3237, N'B27', N'', N'available', CAST(N'2026-04-13T06:05:28.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3238, N'B12', N'', N'occupied', CAST(N'2026-04-13T06:05:39.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3239, N'B20', N'', N'occupied', CAST(N'2026-04-13T06:06:02.480' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3240, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-13T06:06:04.087' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3241, N'B10_CTO', N'NDD-4141', N'occupied', CAST(N'2026-04-13T06:06:21.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3242, N'G6', N'', N'occupied', CAST(N'2026-04-13T06:06:23.690' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3243, N'B27', N'', N'occupied', CAST(N'2026-04-13T06:06:27.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3244, N'G2', N'', N'occupied', CAST(N'2026-04-13T06:06:27.620' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3245, N'B10_CTO', N'', N'available', CAST(N'2026-04-13T06:06:48.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3246, N'B8', N'', N'occupied', CAST(N'2026-04-13T06:06:54.610' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3247, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-13T06:06:54.623' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3248, N'G6', N'', N'available', CAST(N'2026-04-13T06:06:56.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3249, N'G2', N'', N'available', CAST(N'2026-04-13T06:06:56.820' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3250, N'B20', N'', N'available', CAST(N'2026-04-13T06:07:05.833' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3251, N'B8', N'', N'available', CAST(N'2026-04-13T06:07:05.990' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3252, N'B10_CTO', N'', N'available', CAST(N'2026-04-13T06:07:06.003' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3253, N'G6', N'', N'occupied', CAST(N'2026-04-13T06:07:07.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3254, N'GMIA', N'', N'occupied', CAST(N'2026-04-13T06:07:08.200' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3255, N'B3_CEO', N'', N'available', CAST(N'2026-04-13T06:07:17.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3256, N'GMIA', N'', N'available', CAST(N'2026-04-13T06:07:20.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3257, N'B20', N'', N'occupied', CAST(N'2026-04-13T06:07:24.050' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3258, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-13T06:07:24.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3259, N'G6', N'', N'available', CAST(N'2026-04-13T06:07:24.903' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3260, N'B8', N'', N'occupied', CAST(N'2026-04-13T06:07:28.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3261, N'B21', N'', N'occupied', CAST(N'2026-04-13T06:08:38.640' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3262, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-13T06:08:57.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3263, N'B1_CRO', N'', N'available', CAST(N'2026-04-13T06:09:08.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3264, N'B20', N'', N'available', CAST(N'2026-04-13T06:10:14.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3265, N'B8', N'', N'available', CAST(N'2026-04-13T06:10:14.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3266, N'B10_CTO', N'', N'available', CAST(N'2026-04-13T06:10:14.223' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3267, N'B8', N'', N'occupied', CAST(N'2026-04-13T06:11:22.793' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3268, N'G6', N'', N'occupied', CAST(N'2026-04-13T06:11:23.287' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3269, N'G2', N'', N'occupied', CAST(N'2026-04-13T06:11:24.033' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3270, N'B27', N'', N'available', CAST(N'2026-04-13T06:11:29.143' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3271, N'G3', N'', N'available', CAST(N'2026-04-13T06:11:32.040' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3272, N'B21', N'', N'available', CAST(N'2026-04-13T06:11:36.813' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3273, N'B21', N'', N'occupied', CAST(N'2026-04-13T06:11:47.720' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3274, N'B24', N'', N'available', CAST(N'2026-04-13T06:11:54.807' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3275, N'B8', N'', N'available', CAST(N'2026-04-13T06:11:54.950' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3276, N'B8', N'', N'occupied', CAST(N'2026-04-13T06:12:09.593' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3277, N'B24', N'', N'occupied', CAST(N'2026-04-13T06:12:09.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3278, N'B12', N'', N'available', CAST(N'2026-04-13T06:12:17.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3279, N'B21', N'', N'available', CAST(N'2026-04-13T06:12:38.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3280, N'B21', N'', N'occupied', CAST(N'2026-04-13T06:12:42.747' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3281, N'G4', N'', N'occupied', CAST(N'2026-04-13T06:12:55.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3282, N'B12', N'', N'occupied', CAST(N'2026-04-13T08:10:25.610' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3283, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-13T08:10:25.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3284, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-13T08:10:25.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3285, N'GMIA', N'', N'occupied', CAST(N'2026-04-13T08:10:25.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3286, N'B20', N'', N'occupied', CAST(N'2026-04-13T08:10:25.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3287, N'B23', N'', N'occupied', CAST(N'2026-04-13T08:10:25.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3288, N'B14', N'', N'occupied', CAST(N'2026-04-13T08:10:25.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3289, N'B27', N'', N'occupied', CAST(N'2026-04-13T08:10:25.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3290, N'B18', N'', N'occupied', CAST(N'2026-04-13T08:10:27.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3291, N'G5', N'', N'available', CAST(N'2026-04-13T08:10:35.287' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3292, N'B25', N'', N'available', CAST(N'2026-04-13T08:10:35.487' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3293, N'B23', N'', N'available', CAST(N'2026-04-13T08:10:53.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3294, N'B6_Reserved', N'', N'available', CAST(N'2026-04-13T08:10:56.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3295, N'B18', N'', N'available', CAST(N'2026-04-13T08:10:56.840' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3296, N'B13_COO', N'', N'occupied', CAST(N'2026-04-13T08:11:54.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3297, N'B18', N'', N'occupied', CAST(N'2026-04-13T08:12:00.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3298, N'B23', N'', N'occupied', CAST(N'2026-04-13T08:12:04.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3299, N'B13_COO', N'', N'available', CAST(N'2026-04-13T08:12:21.127' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3300, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-13T08:12:28.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3301, N'B23', N'', N'available', CAST(N'2026-04-13T08:12:33.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3302, N'B18', N'', N'available', CAST(N'2026-04-13T08:12:37.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3303, N'B25', N'', N'occupied', CAST(N'2026-04-13T08:12:48.053' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3304, N'B13_COO', N'', N'occupied', CAST(N'2026-04-13T08:12:48.350' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3305, N'B18', N'', N'occupied', CAST(N'2026-04-13T08:12:49.080' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3306, N'B6_Reserved', N'', N'available', CAST(N'2026-04-13T08:13:00.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3307, N'B13_COO', N'', N'available', CAST(N'2026-04-13T08:13:41.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3308, N'B25', N'', N'available', CAST(N'2026-04-13T08:13:41.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3309, N'B8', N'', N'available', CAST(N'2026-04-13T08:13:42.220' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3310, N'B18', N'', N'available', CAST(N'2026-04-13T08:13:46.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3311, N'B25', N'', N'occupied', CAST(N'2026-04-13T08:14:01.193' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3312, N'B8', N'', N'occupied', CAST(N'2026-04-13T08:14:06.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3313, N'B18', N'', N'occupied', CAST(N'2026-04-13T08:14:06.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3314, N'B23', N'', N'occupied', CAST(N'2026-04-13T08:14:21.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3315, N'B8', N'', N'available', CAST(N'2026-04-13T08:14:27.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3316, N'B23', N'', N'available', CAST(N'2026-04-13T08:14:37.313' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3317, N'B13_COO', N'', N'occupied', CAST(N'2026-04-13T08:14:49.713' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3318, N'B23', N'', N'occupied', CAST(N'2026-04-13T08:14:53.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3319, N'B2', N'', N'available', CAST(N'2026-04-13T08:15:00.433' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3320, N'B2', N'', N'occupied', CAST(N'2026-04-13T08:15:21.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3321, N'B23', N'', N'available', CAST(N'2026-04-13T08:15:39.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3322, N'B23', N'', N'occupied', CAST(N'2026-04-13T08:15:42.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3323, N'B13_COO', N'', N'available', CAST(N'2026-04-13T08:16:14.120' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3324, N'B25', N'', N'available', CAST(N'2026-04-13T08:16:14.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3325, N'B2', N'', N'available', CAST(N'2026-04-13T08:16:15.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3326, N'B20', N'', N'available', CAST(N'2026-04-13T08:16:15.200' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3327, N'B13_COO', N'', N'occupied', CAST(N'2026-04-13T08:16:34.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3328, N'B25', N'', N'occupied', CAST(N'2026-04-13T08:16:34.823' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3329, N'B2', N'', N'occupied', CAST(N'2026-04-13T08:16:35.013' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3330, N'B20', N'', N'occupied', CAST(N'2026-04-13T08:16:43.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3331, N'B2', N'', N'available', CAST(N'2026-04-13T08:17:12.710' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3332, N'B2', N'', N'occupied', CAST(N'2026-04-13T08:18:09.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3333, N'B8', N'', N'occupied', CAST(N'2026-04-13T13:25:11.487' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3334, N'G3', N'', N'occupied', CAST(N'2026-04-13T13:25:18.277' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3335, N'B12', N'', N'available', CAST(N'2026-04-13T13:25:24.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3336, N'B2', N'', N'available', CAST(N'2026-04-13T13:25:24.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3337, N'B3_CEO', N'', N'available', CAST(N'2026-04-13T13:25:24.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3338, N'B11_CFO', N'', N'available', CAST(N'2026-04-13T13:25:24.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3339, N'B13_COO', N'', N'available', CAST(N'2026-04-13T13:25:24.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3340, N'B25', N'', N'available', CAST(N'2026-04-13T13:25:24.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3341, N'B24', N'', N'available', CAST(N'2026-04-13T13:25:24.663' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3342, N'B18', N'', N'available', CAST(N'2026-04-13T13:25:24.717' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3343, N'B20', N'', N'available', CAST(N'2026-04-13T13:25:24.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3344, N'B21', N'', N'available', CAST(N'2026-04-13T13:25:24.783' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3345, N'B22', N'', N'available', CAST(N'2026-04-13T13:25:24.827' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3346, N'B15', N'', N'available', CAST(N'2026-04-13T13:25:24.863' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3347, N'B14', N'', N'available', CAST(N'2026-04-13T13:25:24.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3348, N'B27', N'', N'available', CAST(N'2026-04-13T13:25:24.883' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3353, N'G1', N'', N'available', CAST(N'2026-04-13T21:01:01.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3354, N'G2', N'', N'available', CAST(N'2026-04-13T21:01:01.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3355, N'G3', N'', N'available', CAST(N'2026-04-13T21:01:01.257' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3356, N'G1', N'', N'available', CAST(N'2026-04-13T21:01:01.263' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3357, N'G2', N'', N'available', CAST(N'2026-04-13T21:01:01.267' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3358, N'G3', N'', N'available', CAST(N'2026-04-13T21:01:01.273' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3359, N'G4', N'', N'available', CAST(N'2026-04-13T21:01:01.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3360, N'G6', N'', N'available', CAST(N'2026-04-13T21:01:01.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3361, N'G4', N'', N'available', CAST(N'2026-04-13T21:01:01.317' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3362, N'G6', N'', N'available', CAST(N'2026-04-13T21:01:01.320' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3363, N'B8', N'', N'available', CAST(N'2026-04-13T21:01:01.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3364, N'B10_CTO', N'', N'available', CAST(N'2026-04-13T21:01:01.363' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3365, N'B8', N'', N'available', CAST(N'2026-04-13T21:01:01.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3366, N'B10_CTO', N'', N'available', CAST(N'2026-04-13T21:01:01.373' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3367, N'B9', N'', N'available', CAST(N'2026-04-13T21:01:01.480' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3368, N'B9', N'', N'available', CAST(N'2026-04-13T21:01:01.487' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3369, N'GMIA', N'', N'available', CAST(N'2026-04-13T21:01:01.530' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3370, N'GMIA', N'', N'available', CAST(N'2026-04-13T21:01:01.537' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3371, N'B23', N'', N'available', CAST(N'2026-04-13T21:01:01.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3372, N'B23', N'', N'available', CAST(N'2026-04-13T21:01:01.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3373, N'G1', N'', N'occupied', CAST(N'2026-04-14T05:07:20.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3374, N'G1', N'', N'occupied', CAST(N'2026-04-14T05:07:20.927' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3375, N'G4', N'', N'occupied', CAST(N'2026-04-14T05:07:20.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3376, N'G4', N'', N'occupied', CAST(N'2026-04-14T05:07:20.977' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3377, N'B12', N'', N'occupied', CAST(N'2026-04-14T05:07:21.017' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3378, N'B12', N'', N'occupied', CAST(N'2026-04-14T05:07:21.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3379, N'B2', N'', N'occupied', CAST(N'2026-04-14T05:07:21.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3380, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:07:21.083' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3381, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:07:21.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3382, N'B2', N'', N'occupied', CAST(N'2026-04-14T05:07:21.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3383, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:07:21.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3384, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:07:21.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3385, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T05:07:21.163' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3386, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T05:07:21.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3387, N'B9', N'', N'occupied', CAST(N'2026-04-14T05:07:21.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3388, N'B9', N'', N'occupied', CAST(N'2026-04-14T05:07:21.223' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3389, N'B15', N'', N'occupied', CAST(N'2026-04-14T05:07:21.437' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3390, N'B15', N'', N'occupied', CAST(N'2026-04-14T05:07:21.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3391, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:07:47.397' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3392, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:07:47.403' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3393, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T05:08:12.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3394, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T05:08:12.190' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3395, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:08:14.840' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3396, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:08:14.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3397, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:08:30.377' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3398, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:08:30.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3399, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T05:08:31.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3400, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T05:08:31.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3401, N'GMIA', N'', N'available', CAST(N'2026-04-14T05:08:32.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3402, N'GMIA', N'', N'available', CAST(N'2026-04-14T05:08:32.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3403, N'G6', N'', N'available', CAST(N'2026-04-14T05:08:38.333' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3404, N'G6', N'', N'available', CAST(N'2026-04-14T05:08:38.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3405, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:09:05.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3406, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:09:05.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3407, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:09:13.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3408, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:09:13.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3409, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T05:09:58.993' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3410, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T05:09:59.017' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3411, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:10:01.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3412, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:10:01.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3413, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:10:23.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3414, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:10:23.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3415, N'G4', N'', N'available', CAST(N'2026-04-14T05:11:59.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3416, N'G4', N'', N'available', CAST(N'2026-04-14T05:11:59.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3417, N'G4', N'', N'occupied', CAST(N'2026-04-14T05:12:14.713' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3418, N'G4', N'', N'occupied', CAST(N'2026-04-14T05:12:14.750' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3419, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:12:28.760' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3420, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:12:28.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3421, N'B25', N'', N'occupied', CAST(N'2026-04-14T05:12:33.367' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3422, N'B25', N'', N'occupied', CAST(N'2026-04-14T05:12:33.377' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3423, N'G4', N'', N'available', CAST(N'2026-04-14T05:12:50.857' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3424, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:12:50.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3425, N'G4', N'', N'available', CAST(N'2026-04-14T05:12:50.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3426, N'V2_Violation_2', N'', N'available', CAST(N'2026-04-14T05:12:50.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3427, N'G5', N'', N'occupied', CAST(N'2026-04-14T05:19:02.000' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3428, N'G5', N'', N'occupied', CAST(N'2026-04-14T05:19:02.017' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3429, N'G2', N'', N'occupied', CAST(N'2026-04-14T05:19:02.863' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3430, N'G2', N'', N'occupied', CAST(N'2026-04-14T05:19:02.870' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3431, N'G6', N'', N'available', CAST(N'2026-04-14T05:19:14.207' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3432, N'G6', N'', N'available', CAST(N'2026-04-14T05:19:14.217' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3433, N'B12', N'', N'available', CAST(N'2026-04-14T05:20:18.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3434, N'B12', N'', N'available', CAST(N'2026-04-14T05:20:18.913' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3435, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:21:37.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3436, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:21:37.337' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3437, N'G3', N'', N'available', CAST(N'2026-04-14T05:22:20.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3438, N'G3', N'', N'available', CAST(N'2026-04-14T05:22:20.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3439, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:24:41.480' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3440, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:24:41.493' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3441, N'G1', N'', N'available', CAST(N'2026-04-14T05:26:20.487' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3442, N'G1', N'', N'available', CAST(N'2026-04-14T05:26:20.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3443, N'G3', N'', N'available', CAST(N'2026-04-14T05:26:36.840' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3444, N'G3', N'', N'available', CAST(N'2026-04-14T05:26:36.847' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3445, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:27:21.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3446, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:27:21.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3447, N'G3', N'', N'available', CAST(N'2026-04-14T05:28:57.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3448, N'G3', N'', N'available', CAST(N'2026-04-14T05:28:57.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3449, N'G1', N'', N'occupied', CAST(N'2026-04-14T05:36:05.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3450, N'G1', N'', N'occupied', CAST(N'2026-04-14T05:36:05.117' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3451, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:36:06.057' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3452, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:36:06.063' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3453, N'B12', N'', N'occupied', CAST(N'2026-04-14T05:36:08.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3454, N'B12', N'', N'occupied', CAST(N'2026-04-14T05:36:08.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3455, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T05:36:27.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3456, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T05:36:27.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3457, N'B8', N'', N'occupied', CAST(N'2026-04-14T05:36:42.723' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3458, N'B8', N'', N'occupied', CAST(N'2026-04-14T05:36:42.730' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3459, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:37:40.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3460, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:37:40.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3461, N'G6', N'', N'available', CAST(N'2026-04-14T05:37:51.043' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3462, N'G6', N'', N'available', CAST(N'2026-04-14T05:37:51.060' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3463, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T05:38:23.167' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3464, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T05:38:23.180' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3465, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:39:07.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3466, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:39:07.673' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3467, N'B8', N'', N'available', CAST(N'2026-04-14T05:39:47.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3468, N'B8', N'', N'available', CAST(N'2026-04-14T05:39:47.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3469, N'B11_CFO', N'', N'available', CAST(N'2026-04-14T05:39:50.770' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3470, N'B11_CFO', N'', N'available', CAST(N'2026-04-14T05:39:50.780' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3471, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:40:30.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3472, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:40:30.810' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3473, N'B15', N'', N'available', CAST(N'2026-04-14T05:40:48.293' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3474, N'B15', N'', N'available', CAST(N'2026-04-14T05:40:48.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3475, N'B15', N'', N'occupied', CAST(N'2026-04-14T05:41:00.583' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3476, N'B15', N'', N'occupied', CAST(N'2026-04-14T05:41:00.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3477, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:42:52.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3478, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:42:52.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3479, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:43:24.593' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3480, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:43:24.603' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3481, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:43:52.440' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3482, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:43:52.453' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3483, N'G2', N'', N'available', CAST(N'2026-04-14T05:45:36.397' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3484, N'G2', N'', N'available', CAST(N'2026-04-14T05:45:36.417' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3485, N'B12', N'', N'available', CAST(N'2026-04-14T05:45:38.823' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3486, N'B12', N'', N'available', CAST(N'2026-04-14T05:45:38.833' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3487, N'B13_COO', N'', N'available', CAST(N'2026-04-14T05:45:38.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3488, N'B13_COO', N'', N'available', CAST(N'2026-04-14T05:45:39.007' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3489, N'G5', N'', N'available', CAST(N'2026-04-14T05:45:42.427' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3490, N'G5', N'', N'available', CAST(N'2026-04-14T05:45:42.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3491, N'G3', N'', N'available', CAST(N'2026-04-14T05:45:45.397' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3492, N'G3', N'', N'available', CAST(N'2026-04-14T05:45:45.413' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3493, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T05:45:45.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3494, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T05:45:45.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3495, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T05:45:57.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3496, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T05:45:57.270' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3497, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:46:52.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3498, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T05:46:52.943' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3499, N'B12', N'NXR-2727', N'occupied', CAST(N'2026-04-14T05:46:53.327' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3500, N'B12', N'NXR-2727', N'occupied', CAST(N'2026-04-14T05:46:53.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3501, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:46:55.677' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3502, N'B1_CRO', N'', N'occupied', CAST(N'2026-04-14T05:46:55.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3503, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T05:46:55.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3504, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T05:46:55.807' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3505, N'B11_CFO', N'', N'available', CAST(N'2026-04-14T05:47:11.620' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3506, N'B11_CFO', N'', N'available', CAST(N'2026-04-14T05:47:11.630' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3507, N'G5', N'', N'occupied', CAST(N'2026-04-14T05:47:13.693' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3508, N'G5', N'', N'occupied', CAST(N'2026-04-14T05:47:13.703' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3509, N'G2', N'', N'occupied', CAST(N'2026-04-14T05:47:21.740' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3510, N'G2', N'', N'occupied', CAST(N'2026-04-14T05:47:21.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3511, N'G6', N'', N'available', CAST(N'2026-04-14T05:47:31.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3512, N'G6', N'', N'available', CAST(N'2026-04-14T05:47:31.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3513, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:47:37.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3514, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:47:37.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3515, N'B18', N'', N'occupied', CAST(N'2026-04-14T05:48:08.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3516, N'B18', N'', N'occupied', CAST(N'2026-04-14T05:48:08.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3517, N'G6', N'', N'available', CAST(N'2026-04-14T05:48:23.527' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3518, N'G6', N'', N'available', CAST(N'2026-04-14T05:48:23.540' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3519, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:48:27.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3520, N'B1_CRO', N'', N'available', CAST(N'2026-04-14T05:48:27.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3521, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:48:43.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3522, N'G3', N'', N'occupied', CAST(N'2026-04-14T05:48:43.270' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3523, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:48:45.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3524, N'G6', N'', N'occupied', CAST(N'2026-04-14T05:48:45.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3525, N'B21', N'', N'occupied', CAST(N'2026-04-14T05:48:53.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3526, N'B21', N'', N'occupied', CAST(N'2026-04-14T05:48:53.587' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3527, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-14T05:49:09.753' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3528, N'V1_Violation_1', N'', N'occupied', CAST(N'2026-04-14T05:49:09.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3529, N'G2', N'', N'available', CAST(N'2026-04-14T05:49:59.280' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3530, N'G2', N'', N'available', CAST(N'2026-04-14T05:49:59.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3531, N'B18', N'', N'available', CAST(N'2026-04-14T05:50:01.083' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3532, N'B18', N'', N'available', CAST(N'2026-04-14T05:50:01.093' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3533, N'B8', N'', N'occupied', CAST(N'2026-04-14T08:11:15.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3534, N'B8', N'', N'occupied', CAST(N'2026-04-14T08:11:15.357' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3535, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T08:11:15.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3536, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T08:11:15.613' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3537, N'B22', N'', N'occupied', CAST(N'2026-04-14T08:11:16.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3538, N'B22', N'', N'occupied', CAST(N'2026-04-14T08:11:16.033' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3539, N'B17', N'', N'occupied', CAST(N'2026-04-14T08:11:16.613' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3540, N'B17', N'', N'occupied', CAST(N'2026-04-14T08:11:16.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3541, N'B24', N'', N'occupied', CAST(N'2026-04-14T08:11:19.163' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3542, N'B24', N'', N'occupied', CAST(N'2026-04-14T08:11:19.173' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3543, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T08:11:22.010' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3544, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T08:11:22.017' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3545, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-14T08:11:45.163' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3546, N'V1_Violation_1', N'', N'available', CAST(N'2026-04-14T08:11:45.177' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3547, N'G6', N'', N'available', CAST(N'2026-04-14T08:11:45.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3548, N'G6', N'', N'available', CAST(N'2026-04-14T08:11:45.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3549, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:11:45.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3550, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:11:45.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3551, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T08:11:46.550' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3552, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T08:11:46.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3553, N'B14', N'', N'occupied', CAST(N'2026-04-14T08:12:03.830' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3554, N'B14', N'', N'occupied', CAST(N'2026-04-14T08:12:03.843' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3555, N'B27', N'', N'occupied', CAST(N'2026-04-14T08:12:12.043' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3556, N'B27', N'', N'occupied', CAST(N'2026-04-14T08:12:12.053' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3557, N'B21', N'', N'available', CAST(N'2026-04-14T08:12:18.203' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3558, N'B21', N'', N'available', CAST(N'2026-04-14T08:12:18.210' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3559, N'B18', N'', N'occupied', CAST(N'2026-04-14T08:12:33.007' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3560, N'B20', N'', N'occupied', CAST(N'2026-04-14T08:12:33.017' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3561, N'B18', N'', N'occupied', CAST(N'2026-04-14T08:12:33.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3562, N'B20', N'', N'occupied', CAST(N'2026-04-14T08:12:33.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3563, N'G2', N'', N'occupied', CAST(N'2026-04-14T08:12:33.567' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3564, N'G2', N'', N'occupied', CAST(N'2026-04-14T08:12:33.577' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3565, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:12:33.617' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3566, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:12:33.623' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3567, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-14T08:12:33.697' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3568, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-14T08:12:33.703' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3569, N'B10_CTO', N'', N'available', CAST(N'2026-04-14T08:12:55.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3570, N'B10_CTO', N'', N'available', CAST(N'2026-04-14T08:12:55.363' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3571, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-14T08:13:08.247' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3572, N'B10_CTO', N'', N'occupied', CAST(N'2026-04-14T08:13:08.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3573, N'G6', N'', N'available', CAST(N'2026-04-14T08:13:22.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3574, N'G6', N'', N'available', CAST(N'2026-04-14T08:13:22.323' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3575, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T08:13:39.513' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3576, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T08:13:39.523' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3577, N'G2', N'', N'available', CAST(N'2026-04-14T08:13:39.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3578, N'G2', N'', N'available', CAST(N'2026-04-14T08:13:39.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3579, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T08:14:41.603' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3580, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T08:14:41.613' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3581, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:14:55.383' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3582, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:14:55.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3583, N'G1', N'', N'available', CAST(N'2026-04-14T08:15:09.143' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3584, N'G1', N'', N'available', CAST(N'2026-04-14T08:15:09.153' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3585, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T08:15:12.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3586, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T08:15:12.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3587, N'G6', N'', N'available', CAST(N'2026-04-14T08:15:14.493' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3588, N'G6', N'', N'available', CAST(N'2026-04-14T08:15:14.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3589, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:15:49.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3590, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:15:49.263' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3591, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T08:16:07.800' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3592, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T08:16:07.813' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3593, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:16:13.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3594, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:16:13.783' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3595, N'G6', N'', N'available', CAST(N'2026-04-14T08:16:37.863' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3596, N'G6', N'', N'available', CAST(N'2026-04-14T08:16:37.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3597, N'B12', N'', N'available', CAST(N'2026-04-14T08:16:41.923' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3598, N'B12', N'', N'available', CAST(N'2026-04-14T08:16:41.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3599, N'B25', N'', N'available', CAST(N'2026-04-14T08:16:42.750' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3600, N'B25', N'', N'available', CAST(N'2026-04-14T08:16:42.760' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3601, N'G1', N'', N'occupied', CAST(N'2026-04-14T08:16:43.073' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3602, N'G1', N'', N'occupied', CAST(N'2026-04-14T08:16:43.087' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3603, N'B11_CFO', N'', N'available', CAST(N'2026-04-14T08:16:43.283' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3604, N'B11_CFO', N'', N'available', CAST(N'2026-04-14T08:16:43.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3605, N'B8', N'', N'available', CAST(N'2026-04-14T08:16:58.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3606, N'B8', N'', N'available', CAST(N'2026-04-14T08:16:58.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3607, N'G1', N'', N'available', CAST(N'2026-04-14T08:17:04.737' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3608, N'G1', N'', N'available', CAST(N'2026-04-14T08:17:04.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3609, N'B8', N'', N'occupied', CAST(N'2026-04-14T08:17:07.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3610, N'B8', N'', N'occupied', CAST(N'2026-04-14T08:17:07.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3611, N'B25', N'', N'occupied', CAST(N'2026-04-14T08:17:08.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3612, N'B25', N'', N'occupied', CAST(N'2026-04-14T08:17:08.257' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3613, N'B12', N'', N'occupied', CAST(N'2026-04-14T08:17:08.593' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3614, N'B12', N'', N'occupied', CAST(N'2026-04-14T08:17:08.600' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3615, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T08:17:08.743' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3616, N'B11_CFO', N'', N'occupied', CAST(N'2026-04-14T08:17:08.750' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3617, N'G1', N'', N'occupied', CAST(N'2026-04-14T08:17:16.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3618, N'G1', N'', N'occupied', CAST(N'2026-04-14T08:17:16.030' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3619, N'G2', N'', N'occupied', CAST(N'2026-04-14T08:17:24.733' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3620, N'G2', N'', N'occupied', CAST(N'2026-04-14T08:17:24.740' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3621, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T08:17:24.887' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3622, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T08:17:24.897' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3623, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T08:17:31.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3624, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T08:17:31.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3625, N'G2', N'', N'available', CAST(N'2026-04-14T08:17:45.780' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3626, N'G2', N'', N'available', CAST(N'2026-04-14T08:17:45.797' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3627, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T08:17:45.967' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3628, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T08:17:45.977' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3629, N'G1', N'', N'available', CAST(N'2026-04-14T08:18:25.963' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3630, N'G1', N'', N'available', CAST(N'2026-04-14T08:18:25.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3631, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:18:46.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3632, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:18:46.480' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3633, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T08:19:36.080' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3634, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T08:19:36.087' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3635, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:20:31.400' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3636, N'B13_COO', N'', N'available', CAST(N'2026-04-14T08:20:31.410' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3637, N'G1', N'', N'occupied', CAST(N'2026-04-14T08:20:36.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3638, N'G1', N'', N'occupied', CAST(N'2026-04-14T08:20:36.567' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3639, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T08:20:42.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3640, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T08:20:42.943' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3641, N'B8', N'', N'available', CAST(N'2026-04-14T08:20:50.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3642, N'B8', N'', N'available', CAST(N'2026-04-14T08:20:50.353' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3643, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T08:21:46.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3644, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T08:21:46.257' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3645, N'B21', N'', N'occupied', CAST(N'2026-04-14T08:21:46.437' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3646, N'B21', N'', N'occupied', CAST(N'2026-04-14T08:21:46.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3647, N'GMIA', N'', N'available', CAST(N'2026-04-14T08:22:00.357' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3648, N'GMIA', N'', N'available', CAST(N'2026-04-14T08:22:00.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3649, N'B21', N'', N'available', CAST(N'2026-04-14T08:22:11.190' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3650, N'B21', N'', N'available', CAST(N'2026-04-14T08:22:11.200' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3651, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T08:22:11.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3652, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T08:22:11.473' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3653, N'B17', N'', N'available', CAST(N'2026-04-14T08:23:40.993' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3654, N'B18', N'', N'available', CAST(N'2026-04-14T08:23:41.007' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3655, N'B20', N'', N'available', CAST(N'2026-04-14T08:23:41.013' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3656, N'B17', N'', N'available', CAST(N'2026-04-14T08:23:41.020' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3657, N'B18', N'', N'available', CAST(N'2026-04-14T08:23:41.027' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3658, N'B20', N'', N'available', CAST(N'2026-04-14T08:23:41.037' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3659, N'B17', N'', N'occupied', CAST(N'2026-04-14T08:25:37.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3660, N'B18', N'', N'occupied', CAST(N'2026-04-14T08:25:37.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3661, N'B20', N'', N'occupied', CAST(N'2026-04-14T08:25:37.980' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3662, N'B17', N'', N'occupied', CAST(N'2026-04-14T08:25:37.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3663, N'B18', N'', N'occupied', CAST(N'2026-04-14T08:25:37.990' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3664, N'B20', N'', N'occupied', CAST(N'2026-04-14T08:25:37.997' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3665, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T08:27:10.370' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3666, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T08:27:10.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3667, N'GMIA', N'', N'available', CAST(N'2026-04-14T08:27:38.367' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3668, N'GMIA', N'', N'available', CAST(N'2026-04-14T08:27:38.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3669, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:29:21.907' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3670, N'G6', N'', N'occupied', CAST(N'2026-04-14T08:29:21.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3671, N'G2', N'', N'occupied', CAST(N'2026-04-14T08:29:23.423' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3672, N'G2', N'', N'occupied', CAST(N'2026-04-14T08:29:23.430' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3673, N'G3', N'', N'available', CAST(N'2026-04-14T08:29:35.973' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3674, N'G3', N'', N'available', CAST(N'2026-04-14T08:29:35.983' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3675, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T08:29:38.023' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3676, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T08:29:38.033' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3677, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T08:29:53.067' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3678, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T08:29:53.077' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3679, N'B17', N'', N'available', CAST(N'2026-04-14T08:32:09.627' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3680, N'B18', N'', N'available', CAST(N'2026-04-14T08:32:09.640' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3681, N'B20', N'', N'available', CAST(N'2026-04-14T08:32:09.647' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3682, N'B17', N'', N'available', CAST(N'2026-04-14T08:32:09.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3683, N'B18', N'', N'available', CAST(N'2026-04-14T08:32:09.660' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3684, N'B20', N'', N'available', CAST(N'2026-04-14T08:32:09.667' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3685, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T09:17:45.440' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3686, N'GMIA', N'', N'occupied', CAST(N'2026-04-14T09:17:45.460' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3687, N'B17', N'', N'occupied', CAST(N'2026-04-14T09:17:45.560' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3688, N'B18', N'', N'occupied', CAST(N'2026-04-14T09:17:45.570' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3689, N'B20', N'', N'occupied', CAST(N'2026-04-14T09:17:45.580' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3690, N'B17', N'', N'occupied', CAST(N'2026-04-14T09:17:45.583' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3691, N'B18', N'', N'occupied', CAST(N'2026-04-14T09:17:45.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3692, N'B20', N'', N'occupied', CAST(N'2026-04-14T09:17:45.593' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3693, N'G3', N'', N'occupied', CAST(N'2026-04-14T09:17:45.773' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3694, N'G3', N'', N'occupied', CAST(N'2026-04-14T09:17:45.783' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3695, N'G6', N'', N'available', CAST(N'2026-04-14T09:17:58.920' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3696, N'G6', N'', N'available', CAST(N'2026-04-14T09:17:58.930' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3697, N'G2', N'', N'available', CAST(N'2026-04-14T09:17:59.510' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3698, N'G2', N'', N'available', CAST(N'2026-04-14T09:17:59.527' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3699, N'B12', N'', N'available', CAST(N'2026-04-14T09:17:59.687' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3700, N'B12', N'', N'available', CAST(N'2026-04-14T09:17:59.707' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3701, N'B8', N'', N'occupied', CAST(N'2026-04-14T10:13:09.940' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3702, N'B12', N'', N'occupied', CAST(N'2026-04-14T10:13:09.960' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3703, N'B8', N'', N'occupied', CAST(N'2026-04-14T10:13:09.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3704, N'B12', N'', N'occupied', CAST(N'2026-04-14T10:13:09.977' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3705, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:13:10.440' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3706, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:13:10.447' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3707, N'G2', N'', N'occupied', CAST(N'2026-04-14T10:13:10.933' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3708, N'G2', N'', N'occupied', CAST(N'2026-04-14T10:13:10.943' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3709, N'B10_CTO', N'', N'available', CAST(N'2026-04-14T10:13:25.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3710, N'B10_CTO', N'', N'available', CAST(N'2026-04-14T10:13:25.260' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3711, N'B22', N'', N'available', CAST(N'2026-04-14T10:13:25.783' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3712, N'B22', N'', N'available', CAST(N'2026-04-14T10:13:25.790' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3713, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:13:33.680' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3714, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:13:33.690' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3715, N'B8', N'', N'available', CAST(N'2026-04-14T10:13:42.127' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3716, N'B8', N'', N'available', CAST(N'2026-04-14T10:13:42.140' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3717, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T10:13:43.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3718, N'B3_CEO', N'', N'available', CAST(N'2026-04-14T10:13:43.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3719, N'G3', N'', N'available', CAST(N'2026-04-14T10:13:50.287' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3720, N'G3', N'', N'available', CAST(N'2026-04-14T10:13:50.293' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3721, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:14:02.467' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3722, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:14:02.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3723, N'B25', N'', N'available', CAST(N'2026-04-14T10:14:02.547' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3724, N'B25', N'', N'available', CAST(N'2026-04-14T10:14:02.553' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3725, N'B25', N'', N'occupied', CAST(N'2026-04-14T10:14:13.380' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3726, N'B25', N'', N'occupied', CAST(N'2026-04-14T10:14:13.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3727, N'B17', N'', N'available', CAST(N'2026-04-14T10:14:34.837' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3728, N'B18', N'', N'available', CAST(N'2026-04-14T10:14:34.850' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3729, N'B20', N'', N'available', CAST(N'2026-04-14T10:14:34.860' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3730, N'B17', N'', N'available', CAST(N'2026-04-14T10:14:34.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3731, N'B18', N'', N'available', CAST(N'2026-04-14T10:14:34.873' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3732, N'B20', N'', N'available', CAST(N'2026-04-14T10:14:34.877' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3733, N'B12', N'', N'available', CAST(N'2026-04-14T10:14:35.103' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3734, N'B12', N'', N'available', CAST(N'2026-04-14T10:14:35.110' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3735, N'B15', N'', N'available', CAST(N'2026-04-14T10:14:59.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3736, N'B27', N'', N'available', CAST(N'2026-04-14T10:14:59.963' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3737, N'B15', N'', N'available', CAST(N'2026-04-14T10:14:59.970' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3738, N'B27', N'', N'available', CAST(N'2026-04-14T10:14:59.977' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3739, N'G4', N'', N'available', CAST(N'2026-04-14T10:15:18.953' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3740, N'G4', N'', N'available', CAST(N'2026-04-14T10:15:18.963' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3741, N'B15', N'', N'occupied', CAST(N'2026-04-14T10:15:22.290' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3742, N'B27', N'', N'occupied', CAST(N'2026-04-14T10:15:22.303' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3743, N'B15', N'', N'occupied', CAST(N'2026-04-14T10:15:22.307' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3744, N'B27', N'', N'occupied', CAST(N'2026-04-14T10:15:22.313' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3745, N'B15', N'', N'available', CAST(N'2026-04-14T10:16:19.390' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3746, N'B27', N'', N'available', CAST(N'2026-04-14T10:16:19.407' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3747, N'B15', N'', N'available', CAST(N'2026-04-14T10:16:19.417' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3748, N'B27', N'', N'available', CAST(N'2026-04-14T10:16:19.423' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3749, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:17:06.767' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3750, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:17:06.777' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3751, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:17:18.567' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3752, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:17:18.577' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3753, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:17:55.620' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3754, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:17:55.633' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3755, N'B12', N'', N'occupied', CAST(N'2026-04-14T10:17:57.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3756, N'B12', N'', N'occupied', CAST(N'2026-04-14T10:17:57.250' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3757, N'G4', N'', N'available', CAST(N'2026-04-14T10:17:58.947' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3758, N'G4', N'', N'available', CAST(N'2026-04-14T10:17:58.957' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3759, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:18:05.463' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3760, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:18:05.477' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3761, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:18:46.113' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3762, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:18:46.127' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3763, N'B12', N'', N'available', CAST(N'2026-04-14T10:18:49.987' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3764, N'B12', N'', N'available', CAST(N'2026-04-14T10:18:50.000' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3765, N'B12', N'', N'occupied', CAST(N'2026-04-14T10:19:02.300' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3766, N'B12', N'', N'occupied', CAST(N'2026-04-14T10:19:02.310' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3767, N'B12', N'', N'available', CAST(N'2026-04-14T10:20:20.393' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3768, N'B12', N'', N'available', CAST(N'2026-04-14T10:20:20.407' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3769, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:21:16.047' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3770, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:21:16.057' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3771, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:21:30.907' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3772, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:21:30.917' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3773, N'G4', N'', N'available', CAST(N'2026-04-14T10:21:34.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3774, N'G4', N'', N'available', CAST(N'2026-04-14T10:21:34.910' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3775, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T10:22:35.170' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3776, N'B3_CEO', N'', N'occupied', CAST(N'2026-04-14T10:22:35.183' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3777, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T10:22:35.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3778, N'B6_Reserved', N'', N'occupied', CAST(N'2026-04-14T10:22:35.243' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3779, N'B17', N'', N'occupied', CAST(N'2026-04-14T10:22:35.470' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3780, N'B18', N'', N'occupied', CAST(N'2026-04-14T10:22:35.480' AS DateTime))
GO
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3781, N'B20', N'', N'occupied', CAST(N'2026-04-14T10:22:35.483' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3782, N'B17', N'', N'occupied', CAST(N'2026-04-14T10:22:35.490' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3783, N'B18', N'', N'occupied', CAST(N'2026-04-14T10:22:35.500' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3784, N'B20', N'', N'occupied', CAST(N'2026-04-14T10:22:35.507' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3785, N'B21', N'', N'occupied', CAST(N'2026-04-14T10:22:35.557' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3786, N'B21', N'', N'occupied', CAST(N'2026-04-14T10:22:35.563' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3787, N'B15', N'', N'occupied', CAST(N'2026-04-14T10:22:35.637' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3788, N'B27', N'', N'occupied', CAST(N'2026-04-14T10:22:35.643' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3789, N'B15', N'', N'occupied', CAST(N'2026-04-14T10:22:35.650' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3790, N'B27', N'', N'occupied', CAST(N'2026-04-14T10:22:35.653' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3791, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:22:41.890' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3792, N'G4', N'', N'occupied', CAST(N'2026-04-14T10:22:41.900' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3793, N'B21', N'', N'available', CAST(N'2026-04-14T10:23:04.867' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3794, N'B21', N'', N'available', CAST(N'2026-04-14T10:23:04.880' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3795, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T10:23:05.167' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3796, N'B6_Reserved', N'', N'available', CAST(N'2026-04-14T10:23:05.180' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3797, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:23:21.253' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3798, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:23:21.263' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3799, N'B25', N'', N'available', CAST(N'2026-04-14T10:23:21.343' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3800, N'B25', N'', N'available', CAST(N'2026-04-14T10:23:21.350' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3801, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:23:41.233' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3802, N'B13_COO', N'', N'occupied', CAST(N'2026-04-14T10:23:41.240' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3803, N'B25', N'', N'occupied', CAST(N'2026-04-14T10:23:41.283' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3804, N'B25', N'', N'occupied', CAST(N'2026-04-14T10:23:41.293' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3805, N'G4', N'', N'available', CAST(N'2026-04-14T10:23:59.657' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3806, N'G4', N'', N'available', CAST(N'2026-04-14T10:23:59.667' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3807, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:24:37.597' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3808, N'B13_COO', N'', N'available', CAST(N'2026-04-14T10:24:37.607' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3809, N'B2', N'', N'available', CAST(N'2026-04-14T10:24:46.590' AS DateTime))
INSERT [dbo].[slot_status] ([id], [slot_id], [plate_number], [status], [time]) VALUES (3810, N'B2', N'', N'available', CAST(N'2026-04-14T10:24:46.600' AS DateTime))
SET IDENTITY_INSERT [dbo].[slot_status] OFF
SET IDENTITY_INSERT [dbo].[vehicles] ON 

INSERT [dbo].[vehicles] ([id], [plate_number], [owner_name], [vehicle_type], [employee_id], [is_registered], [registered_at], [notes], [title], [is_employee], [phone], [email]) VALUES (9, N'ZXY-123', N'Ahmed alaa', N'sedan', N'452', 1, CAST(N'2026-04-13T01:21:54.437' AS DateTime), N'good', N'eng.', 1, NULL, NULL)
INSERT [dbo].[vehicles] ([id], [plate_number], [owner_name], [vehicle_type], [employee_id], [is_registered], [registered_at], [notes], [title], [is_employee], [phone], [email]) VALUES (10, N'cdf-123', N'Mohamed Henaish', N'cross', N'emp-2', 1, CAST(N'2026-04-13T10:17:29.103' AS DateTime), N'good', N'eng.', 1, NULL, NULL)
INSERT [dbo].[vehicles] ([id], [plate_number], [owner_name], [vehicle_type], [employee_id], [is_registered], [registered_at], [notes], [title], [is_employee], [phone], [email]) VALUES (11, N'kgh-587', N'mohamed gamal', N'suv', N'875', 1, CAST(N'2026-04-14T12:56:19.080' AS DateTime), N'good', N'eng.', 1, NULL, NULL)
SET IDENTITY_INSERT [dbo].[vehicles] OFF
SET IDENTITY_INSERT [dbo].[zone_occupancy] ON 

INSERT [dbo].[zone_occupancy] ([id], [zone_id], [camera_id], [current_count], [max_capacity], [last_updated], [zone_name], [floor]) VALUES (1, N'GARAGE-TOTAL', N'CAM-03', 15, 18, CAST(N'2026-04-13T06:10:46.333' AS DateTime), N'Garage Total', N'ALL')
INSERT [dbo].[zone_occupancy] ([id], [zone_id], [camera_id], [current_count], [max_capacity], [last_updated], [zone_name], [floor]) VALUES (2, N'B1-PARKING', N'CAM-03', 2, 9, CAST(N'2026-04-14T10:27:59.957' AS DateTime), N'B1 Parking', N'B1')
INSERT [dbo].[zone_occupancy] ([id], [zone_id], [camera_id], [current_count], [max_capacity], [last_updated], [zone_name], [floor]) VALUES (3, N'B2-PARKING', N'CAM-09', 13, 9, CAST(N'2026-04-14T10:27:59.963' AS DateTime), N'B2 Parking', N'B2')
SET IDENTITY_INSERT [dbo].[zone_occupancy] OFF
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_alerts_alert_type]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_alerts_alert_type] ON [dbo].[alerts]
(
	[alert_type] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_alerts_slot_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_alerts_slot_id] ON [dbo].[alerts]
(
	[slot_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
/****** Object:  Index [ix_alerts_triggered_at]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_alerts_triggered_at] ON [dbo].[alerts]
(
	[triggered_at] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
/****** Object:  Index [ix_entry_exit_log_event_time]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_entry_exit_log_event_time] ON [dbo].[entry_exit_log]
(
	[event_time] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_entry_exit_log_plate_number]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_entry_exit_log_plate_number] ON [dbo].[entry_exit_log]
(
	[plate_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
/****** Object:  Index [ix_intrusions_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_intrusions_id] ON [dbo].[intrusions]
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_intrusions_plate_number]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_intrusions_plate_number] ON [dbo].[intrusions]
(
	[plate_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
/****** Object:  Index [ix_parking_sessions_entry_time]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_sessions_entry_time] ON [dbo].[parking_sessions]
(
	[entry_time] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
/****** Object:  Index [ix_parking_sessions_exit_time]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_sessions_exit_time] ON [dbo].[parking_sessions]
(
	[exit_time] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_sessions_plate_number]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_sessions_plate_number] ON [dbo].[parking_sessions]
(
	[plate_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_sessions_slot_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_sessions_slot_id] ON [dbo].[parking_sessions]
(
	[slot_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_sessions_status]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_sessions_status] ON [dbo].[parking_sessions]
(
	[status] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_sessions_zone_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_sessions_zone_id] ON [dbo].[parking_sessions]
(
	[zone_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_slots_floor]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_slots_floor] ON [dbo].[parking_slots]
(
	[floor] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_slots_slot_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_slots_slot_id] ON [dbo].[parking_slots]
(
	[slot_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_parking_slots_slot_name]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_parking_slots_slot_name] ON [dbo].[parking_slots]
(
	[slot_name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
/****** Object:  Index [ix_slot_status_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_slot_status_id] ON [dbo].[slot_status]
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_slot_status_plate_number]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE NONCLUSTERED INDEX [ix_slot_status_plate_number] ON [dbo].[slot_status]
(
	[plate_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_vehicles_plate_number]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE UNIQUE NONCLUSTERED INDEX [ix_vehicles_plate_number] ON [dbo].[vehicles]
(
	[plate_number] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON
GO
/****** Object:  Index [ix_zone_occupancy_zone_id]    Script Date: 4/14/2026 3:30:44 PM ******/
CREATE UNIQUE NONCLUSTERED INDEX [ix_zone_occupancy_zone_id] ON [dbo].[zone_occupancy]
(
	[zone_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
ALTER TABLE [dbo].[alerts]  WITH CHECK ADD  CONSTRAINT [fk_alerts_slot_id] FOREIGN KEY([slot_id])
REFERENCES [dbo].[parking_slots] ([slot_id])
GO
ALTER TABLE [dbo].[alerts] CHECK CONSTRAINT [fk_alerts_slot_id]
GO
ALTER TABLE [dbo].[entry_exit_log]  WITH CHECK ADD FOREIGN KEY([matched_entry_id])
REFERENCES [dbo].[entry_exit_log] ([id])
GO
ALTER TABLE [dbo].[entry_exit_log]  WITH CHECK ADD FOREIGN KEY([vehicle_id])
REFERENCES [dbo].[vehicles] ([id])
ON DELETE SET NULL
GO
ALTER TABLE [dbo].[entry_exit_log]  WITH CHECK ADD  CONSTRAINT [fk_entry_exit_log_matched_entry_id] FOREIGN KEY([matched_entry_id])
REFERENCES [dbo].[entry_exit_log] ([id])
GO
ALTER TABLE [dbo].[entry_exit_log] CHECK CONSTRAINT [fk_entry_exit_log_matched_entry_id]
GO
ALTER TABLE [dbo].[entry_exit_log]  WITH CHECK ADD  CONSTRAINT [fk_entry_exit_log_vehicle_id] FOREIGN KEY([vehicle_id])
REFERENCES [dbo].[vehicles] ([id])
GO
ALTER TABLE [dbo].[entry_exit_log] CHECK CONSTRAINT [fk_entry_exit_log_vehicle_id]
GO
ALTER TABLE [dbo].[intrusions]  WITH CHECK ADD FOREIGN KEY([slot_id])
REFERENCES [dbo].[parking_slots] ([slot_id])
GO
ALTER TABLE [dbo].[parking_sessions]  WITH CHECK ADD FOREIGN KEY([vehicle_id])
REFERENCES [dbo].[vehicles] ([id])
GO
ALTER TABLE [dbo].[parking_sessions]  WITH CHECK ADD  CONSTRAINT [fk_parking_sessions_slot_id] FOREIGN KEY([slot_id])
REFERENCES [dbo].[parking_slots] ([slot_id])
GO
ALTER TABLE [dbo].[parking_sessions] CHECK CONSTRAINT [fk_parking_sessions_slot_id]
GO
ALTER TABLE [dbo].[slot_status]  WITH CHECK ADD FOREIGN KEY([slot_id])
REFERENCES [dbo].[parking_slots] ([slot_id])
GO
USE [master]
GO
ALTER DATABASE [damanat_pms] SET  READ_WRITE 
GO
