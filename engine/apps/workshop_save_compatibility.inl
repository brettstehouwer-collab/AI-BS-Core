// Accept exactly today's Workshop registry or its predecessor without changing an open save.
std::vector<ComponentSchema> chapter_save_registry(const Options& options,const GameplayScope& scope,
                                                   const FirstBootContent& content) {
 auto current=first_boot_content_relay_assembly_schemas(content);
 GameplayStoreRecovery saved;
 try {saved=GameplayStore::inspect_recovery(options.database,scope,current);}
 catch(const std::exception&){
  // Both reads use the guarded immutable connection. Scope, full stream and
  // exact registry must pass under one of the two known definitions.
  const auto removed=std::erase_if(current,[](const auto& schema){return schema.type_id==opening_workshop_assembly_component_type;});
  if(removed!=1)throw;
  saved=GameplayStore::inspect_recovery(options.database,scope,current);
 }
 first_boot_content_validate(saved,content);
 return current;
}

// A pre-upgrade copy includes committed WAL pages. Validate its complete event
// stream and present state before publishing the copy or extending the original.
void preserve_workshop_save(const std::filesystem::path& database,const GameplayStoreRecovery& before,
                            const std::vector<ComponentSchema>& schemas) {
 auto target=database;
 target+=L".before-relay-assembly-"+wide(new_uuid())+L".sqlite";
 auto staging=target;
 staging+=L".partial";
 HANDLE claim=CreateFileW(staging.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
 require(claim!=INVALID_HANDLE_VALUE,"Cannot reserve the pre-upgrade Workshop save copy");
 CloseHandle(claim);
 using Connection=std::unique_ptr<sqlite3,decltype(&sqlite3_close)>;
 const auto open=[](const std::filesystem::path& path,int flags){
  sqlite3* raw=nullptr;
  const int result=sqlite3_open_v2(narrow(path.native()).c_str(),&raw,flags,nullptr);
  Connection handle(raw,sqlite3_close);
  require(result==SQLITE_OK,"Cannot open the Workshop save for backup");return handle;
 };
 {
  auto input=open(database,SQLITE_OPEN_READONLY);
  auto output=open(staging,SQLITE_OPEN_READWRITE);
  sqlite3_backup* copy=sqlite3_backup_init(output.get(),"main",input.get(),"main");
  require(copy!=nullptr,"Cannot initialize the Workshop save backup");
  const int copied=sqlite3_backup_step(copy,-1);
  const int finished=sqlite3_backup_finish(copy);
  require(copied==SQLITE_DONE&&finished==SQLITE_OK,"Could not finish the pre-upgrade Workshop save copy");
 }
 const auto check=GameplayStore::inspect_recovery(staging,before.scope,schemas);
 require(check.revision==before.revision&&check.sequence==before.sequence&&check.components==before.components,
         "Pre-upgrade Workshop save differs from its current durable state");
 std::filesystem::rename(staging,target);
}
