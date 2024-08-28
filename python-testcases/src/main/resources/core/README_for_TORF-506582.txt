Install a LITP HW environment with the first iso: 2.99.3
Place all these LITP iso files in /software/LITP on the Management Server.
Execute the testset against this hardware environment and all the JRE upgrade paths shall be tested.

When a newer version of the Server JRE is to be delivered, the test set must be updated to include a new test, which uses the previous latest version as the From-state.
Update this README to include a link the the LITP iso containing the new latest version of the Server JRE.

Also these two variables will need to be updated for the latest

self.litp_iso_to_version
self.java_to_version

ServerJRE to LITP iso mapping:

serverJRE 8u202 (LITP ISO 2.99.3) (EXTRserverjre_CXP9035480 1.5.7) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/19.10/mediaContent/ERIClitp_CXP9024296/2.99.3/)
serverJRE 8u212 (LITP ISO 2.100.5) (EXTRserverjre_CXP9035480 1.6.1) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/19.11/mediaContent/ERIClitp_CXP9024296/2.100.5/)
serverJRE 8u212tz (LITP ISO 2.102.7) (EXTRserverjre_CXP9035480 1.7.2) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/19.13/mediaContent/ERIClitp_CXP9024296/2.102.7/)
serverJRE 8u221 (LITP ISO 2.104.12) (EXTRserverjre_CXP9035480 1.8.2) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/19.15/mediaContent/ERIClitp_CXP9024296/2.104.12/)
serverJRE 8u231 (LITP ISO 2.109.9) (EXTRserverjre_CXP9035480 1.9.2) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/20.03/mediaContent/ERIClitp_CXP9024296/2.109.9/)
serverJRE 8u241 (LITP ISO 2.113.5) (EXTRserverjre_CXP9035480 1.10.1) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/20.07/mediaContent/ERIClitp_CXP9024296/2.113.5/)
serverJRE 8u251 (LITP ISO 2.117.5) (EXTRserverjre_CXP9035480 1.12.2) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/20.11/mediaContent/ERIClitp_CXP9024296/2.117.5/)
serverJRE 8u261 (LITP ISO 2.121.3) (EXTRserverjre_CXP9035480 1.13.3) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/20.15/mediaContent/ERIClitp_CXP9024296/2.121.3/)
ServerJRE 8u281 (LITP ISO 2.128.4) (EXTRserverjre_CXP9035480 1.16.2) (https://ci-portal.seli.wh.rnd.internal.ericsson.com/LITP/21.05/mediaContent/ERIClitp_CXP9024296/2.128.4/)
