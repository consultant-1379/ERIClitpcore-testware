module MCollective
  module Agent
    class Lvmsnapshot<RPC::Agent
      # Basic echo server
      action "create_percentage_snapshot" do
        cmd = "lvcreate -l#{request[:snap_size]}%FREE -s -n #{request[:snap_name]} /dev/#{request[:vg_name]}/#{request[:lv_name]}"
        reply[:status] = run("#{cmd}",
                              :stdout => :out,
                              :stderr => :err,
                              :chomp => true)

      end
      action "create_mb_snapshot" do
        cmd = "lvcreate -L#{request[:snap_size]}M -s -n #{request[:name]} /dev/#{request[:vg_name]}/#{request[:lv_name]}"
        reply[:status] = run("#{cmd}",
                              :stdout => :out,
                              :stderr => :err,
                              :chomp => true)

      end
      action "merge_snapshot" do
        cmd = "lvconvert --merge #{request[:vg_name]}/#{request[:lv_name]}"
        reply[:status] = run("#{cmd}",
                              :stdout => :out,
                              :stderr => :err,
                              :chomp => true)

      end
      action "remove_snapshot" do
        cmd = "lvremove /dev/#{request[:vg_name]}/#{request[:lv_name]} -f"
        reply[:status] = run("#{cmd}",
                              :stdout => :out,
                              :stderr => :err,
                              :chomp => true)

      end
      action "mount_snapshot" do
        cmd = "mkdir -p /mnt/snapshot; mount /dev/#{request[:vg_name]}/#{request[:name]} /mnt/snapshot"
        reply[:status] = run("#{cmd}",
                              :stdout => :out,
                              :stderr => :err,
                              :chomp => true)

      end
      action "umount_snapshot" do
        cmd = "umount /mnt/snapshot"
        reply[:status] = run("#{cmd}",
                              :stdout => :out,
                              :stderr => :err,
                              :chomp => true)

      end
    end
  end
end
# Usage:
# mco rpc --agent lvmsnapshot --action create_percentage_snapshot --argument snap_size=10 --argument vg_name=vg_ms1 --argument  lv_name=lv_root --argument snap_name=root_snap -I ms1
# mco rpc --agent lvmsnapshot --action create_mb_snapshot --argument snap_size=10 --argument vg_name=vg_ms1 --argument  lv_name=lv_root --argument snap_name=root_snap -I ms1
# mco rpc --agent lvmsnapshot --action merge_snapshot --argument vg_name=vg_ms1 --argument  lv_name=lv_root  -I ms1
# mco rpc --agent lvmsnapshot --action remove_snapshot --argument vg_name=vg_ms1 --argument  lv_name=lv_root  -I ms1
# mco rpc --agent lvmsnapshot --action mount_snapshot --argument vg_name=vg_ms1 --argument  lv_name=lv_root  -I ms1
# mco rpc --agent lvmsnapshot --action umount_snapshot
#
#
