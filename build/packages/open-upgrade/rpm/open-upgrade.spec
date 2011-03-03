%define INIT_DIR /etc/init.d
%define _sysconfdir /etc

Name: 		%{RpmName}
Summary: 	Upgrade helper package for Likewise Open
Version: 	%{RpmVersion}
Release: 	%{RpmRelease}
License: 	Likewise Proprietary
URL: 		http://www.likewise.com/
Group: 		System Environment/Daemons
BuildRoot: 	%{buildRootDir}/%{name}-%{version}
Prereq: grep, sh-utils
AutoReq: no

%description
Likewise provides Active Directory authentication.

%prep

%build

%install
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT
rsync -a %{PopulateRoot}/ ${RPM_BUILD_ROOT}/

%clean
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root)

%if ! %{Compat32}
%pre

UPGRADEDIR=/opt/likewise-upgrade

LOG=/var/log/likewise-open-install.log
TLOG=/tmp/LikewiseOpenTemp.txt

DAEMONS_TO_HALT="lwmgmtd lwrdrd npcmuxd likewise-open likewise-winbindd centeris.com-lwiauthd centeris.com-gpagentd lwsmd lwregd netlogond lwiod dcerpcd eventlogd lsassd reapsysld"

# Display to screen and log file with a blank line between entries.
log()
{
    echo $@
    echo
    echo $@ >> $LOG
    echo >> $LOG
}

# Display to screen and log file with no blank line.
_log()
{
    echo $@
    echo $@ >> $LOG
}

# Display to file.
logfile()
{
    echo $@ >> $LOG
    echo >> $LOG
}

# Execute command.
# If successful, note in log file.
# If not successful, note on screen and log file.
run()
{
    $@ > $TLOG 2>&1
    err=$?
    if [ $err -eq 0 ]; then
        echo "Success: $@" >> $LOG
        cat $TLOG >> $LOG
        echo >> $LOG
    else
        _log "Error: $@ returned $err"
        _log `cat $TLOG`
        _log
    fi
    rm -f $TLOG > /dev/null 2>&1
    return $err
}

# Execute command.
# Log only to file.
run_quiet()
{
    $@ > $TLOG 2>&1
    err=$?
    if [ $err -eq 0 ]; then
        echo "Success: $@" >> $LOG
    else
        echo "Error: $@ returned $err  (ignoring and continuing)" >> $LOG
    fi
    cat $TLOG >> $LOG
    echo >> $LOG
    rm -f $TLOG > /dev/null 2>&1
    return $err
}

# Execute command.
# If successful, note in log file.
# If not successful, note on screen and log file and then exit.
run_or_fail()
{
    $@ > $TLOG 2>&1
    err=$?
    if [ $err -eq 0 ]; then
        echo "Success: $@" >> $LOG
        cat $TLOG >> $LOG
        echo >> $LOG
    else
        _log "Error: $@ returned $err  (aborting this script)"
        _log `cat $TLOG`
        _log
        rm -f $TLOG > /dev/null 2>&1
        exit 1
    fi
    rm -f $TLOG > /dev/null 2>&1
    return $err
}

determine_upgrade_type()
{
    VERSIONFILE=/opt/likewise/data/VERSION
    ENTERPRISE_VERSIONFILE=/opt/likewise/data/ENTERPRISE_VERSION

    if [ -f $ENTERPRISE_VERSIONFILE ]; then
        log "$ENTERPRISE_VERSIONFILE exists: Uninstall Likewise Enterprise before proceeding."
        exit 1
    elif [ -f /opt/likewise/sbin/gpagentd ]; then
        log "/opt/likewise/sbin/gpagentd exists: Uninstall Likewise Enterprise before proceeding."
        exit 1
    fi

    if [ -f $VERSIONFILE ]; then
        run_or_fail "mkdir -p ${UPGRADEDIR}"
        run_or_fail "cp $VERSIONFILE ${UPGRADEDIR}"

        run_or_fail "cat $VERSIONFILE"
        if [ -n "`grep '^VERSION=5.0' $VERSIONFILE`" ]; then
            UPGRADING_FROM_5_0123=1
            log "Preserving 5.0 configuration in ${UPGRADEDIR}."
        elif [ -n "`grep '^VERSION=5.1' $VERSIONFILE`" ]; then
            UPGRADING_FROM_5_0123=1
            log "Preserving 5.1 configuration in ${UPGRADEDIR}."
        elif [ -n "`grep '^VERSION=5.2' $VERSIONFILE`" ]; then
            UPGRADING_FROM_5_0123=1
            log "Preserving 5.2 configuration in ${UPGRADEDIR}."
        elif [ -n "`grep '^VERSION=5.3' $VERSIONFILE`" ]; then
            UPGRADING_FROM_5_0123=1
            log "Preserving 5.3 configuration in ${UPGRADEDIR}."
        elif [ -n "`grep '^VERSION=6.0' $VERSIONFILE`" ]; then
            UPGRADING_FROM_6_0=1
            log "Preserving 6.0 configuration in ${UPGRADEDIR}."
        fi
    fi
}

preserve_5_0123_configuration()
{
    if [ -n "${UPGRADING_FROM_5_0123}" ]; then
        if [ -f "/etc/likewise/eventlogd.conf" ]; then
            run_or_fail "cp /etc/likewise/eventlogd.conf ${UPGRADEDIR}"
        fi

        if [ -f "/etc/likewise/lsassd.conf" ]; then
            run_or_fail "cp /etc/likewise/lsassd.conf ${UPGRADEDIR}"
        fi

        if [ -f "/etc/likewise/netlogon.conf" ]; then
            run_or_fail "cp /etc/likewise/netlogon.conf ${UPGRADEDIR}"
        fi

        if [ -f "/var/lib/likewise/db/pstore.db" ]; then
            run_or_fail "cp /var/lib/likewise/db/pstore.db ${UPGRADEDIR}"
            run_or_fail "chmod 700 ${UPGRADEDIR}/pstore.db"
        fi
    fi
}

preserve_6_0_configuration()
{
    # Nothing to do for 6.0 -- all files will be upgraded in place
    return 0
}

preinstall()
{
    log "Package: Likewise Open Upgrade begins (`date`)"

    determine_upgrade_type

    # Try to deconfigure pam/nsswitch
    if [ -x /opt/likewise/bin/domainjoin-cli ]; then
        run_quiet "/opt/likewise/bin/domainjoin-cli configure --disable pam"
        run_quiet "/opt/likewise/bin/domainjoin-cli configure --disable nsswitch"
    fi

    # Stop any Likewise daemons
    if [ -x /opt/likewise/bin/lwsm ]; then
        run_quiet "/opt/likewise/bin/lwsm shutdown"
    fi
    for daemon in $DAEMONS_TO_HALT; do
        if [ -x /etc/rc.d/$daemon ]; then
            run_quiet "/etc/rc.d/$daemon stop"
        fi
        run_quiet "pkill -KILL -x $daemon"
    done

    preserve_5_0123_configuration

    preserve_6_0_configuration

    log "Package: Likewise Open Upgrade finished"
    exit 0
}

preinstall

%endif

%changelog
