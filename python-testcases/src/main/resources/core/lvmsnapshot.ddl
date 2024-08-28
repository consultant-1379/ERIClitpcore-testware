metadata :name        => "lvm_snapshot",
         :description => "Agent to handle lvm snapshots",
         :author      => "Marcin Spoczynski",
         :license     => "BSD",
         :version     => "1.0",
         :url         => "http://ammeon.com/",
         :timeout     => 10

action "create_percentage_snapshot", :description => "Create snapshot" do

    display :always

    input :snap_size,
          :prompt      => "Snap Size",
          :description => "Snap Size",
          :type        => :integer,
          :validation  => '^[0-9]+$',
          :optional    => false,
          :maxlength   => 3

    input :vg_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. vg_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    input :lv_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. lv_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    input :snap_name,
          :prompt      => "Snap Name",
          :description => "Smap Name eg. snapshot",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    output :status,
           :description => "The output of the command",
           :display_as  => "Command result",                                                                                                                                               :default     => "no output"                                                                                                                                                                                                                                                           
    summarize do                                                              
      aggregate summary(:status)
    end                                                                                                                                                                                                                                                                                          
end
action "create_mb_snapshot", :description => "Create snapshot with snap_size value in MB" do

    display :always

    input :snap_size,
          :prompt      => "Snap Size",
          :description => "Snap Size in MB",
          :type        => :integer,
          :validation  => '^[0-9]+$',
          :optional    => false,
          :maxlength   => 3

    input :vg_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. vg_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    input :lv_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. lv_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    input :snap_name,
          :prompt      => "Snap Name",
          :description => "Smap Name eg. snapshot",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    output :status,
           :description => "The output of the command",
           :display_as  => "Command result",                                                                                                                                               :default     => "no output"                                                                                                                                                                                                                                                           
    summarize do                                                              
      aggregate summary(:status)
    end                                                                                                                                                                                                                                                                                          
end

action "merge_snapshot", :description => "Merge snapshot" do

    display :always

    input :vg_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. vg_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    input :lv_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. lv_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    output :status,
           :description => "The output of the command",
           :display_as  => "Command result",                                                                                                                                               :default     => "no output"                                                                                                                                                                                                                                                           
    summarize do                                                              
      aggregate summary(:status)
    end                                                                                                                                                                                                                                                                                          
end

action "remove_snapshot", :description => "Remove snapshot" do

    display :always

    input :vg_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. vg_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    input :lv_name,
          :prompt      => "Volume Group Name",
          :description => "Volume Group Name eg. lv_root",
          :type        => :string,
          :validation  => '^[A-Za-z0-9._]+$',
          :optional    => false,
          :maxlength   => 30

    output :status,
           :description => "The output of the command",
           :display_as  => "Command result",                                                                                                                                               :default     => "no output"                                                                                                                                                                                                                                                           
    summarize do                                                              
      aggregate summary(:status)
    end                                                                                                                                                                                                                                                                                          
end

action "umount_snapshot", :description => "Umount snapshot" do

    display :always

    output :status,
           :description => "The output of the command",
           :display_as  => "Command result",                                                                                                                                               :default     => "no output"                                                                                                                                                                                                                                                           
    summarize do                                                              
      aggregate summary(:status)
    end                                                                                                                                                                                                                                                                                          
end
