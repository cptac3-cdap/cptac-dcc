#!/bin/sh
# set -x
TEST=/Phase_II_Data/CompRef/CompRef_Proteome_BI
TEST1=CompRef_Proteome_BI_mzML.cksum
rm -f "$TEST1"
ASPERA_SCP_COOKIE="COOKIE-TESTING-STRING"
export ASPERA_SCP_COOKIE
../aspera/Linux64/bin/ascp -i `pwd`/../aspera/Linux64/etc/asperaweb_id_dsa.openssh -P 33001 -O 33001 -T -Q -u "CMDLINE-TESTING-STRING" --user public --host cptc-xfer.uis.georgetown.edu --mode recv $TEST/$TEST1 .
echo -n " cksum: "
cksum < "$TEST1"
echo "expect: 2236355677 3274"
rm -f "$TEST1"
