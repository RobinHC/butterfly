import os
from subprocess import PIPE, Popen
import sys


class RunManager(object):
    """butterfly RunManager class.

    Use this class to create files that are needed to run a case.
    """
    shellinit = None
    containerId = None

    def __init__(self, projectName):
        """Init run manager for project.

        Project path will be set to: C:/Users/%USERNAME%/butterfly/projectName
        """
        assert os.name == 'nt', "Currently RunManager is only supported on Windows."
        self.projectName = projectName

    def getShellinit(self):
        """Get shellinit for setting up initial environment for docker."""
        os.environ['PATH'] += ';%s' % r'C:\Program Files (x86)\Git\bin'
        os.environ['PATH'] += ';%s' % r'C:\Program Files\Boot2Docker for Windows'
        process = Popen('boot2docker shellinit', shell=True, stdout=PIPE,
                        stderr=PIPE)
        return tuple(line.replace('$Env:', 'set ')
                    .replace(' = ', '=')
                    .replace('"', '').strip()
                    for line in process.stdout)

    def getContainerId(self, name='of_plus_300'):
        """Get OpenFOAM's container id."""
        # It seems to always be the same number: 63915d16038d
        _id = None
        if not self.shellinit:
            self.shellinit = self.getShellinit()

        # write a batch file
        _BFFolder = r"C:\Users\%s\butterfly" % os.environ['USERNAME']
        _batchFile = os.path.join(_BFFolder, 'getid.bat')
        with open(_batchFile, 'wb') as outf:
            outf.write("\n".join(self.shellinit))
            outf.write("\ndocker ps")

        p = Popen(_batchFile, shell=True, stdout=PIPE, stderr=PIPE)

        if tuple(p.stderr):
            for line in p.stderr:
                print line
            return

        for count, line in enumerate(p.stdout):
            if line.find('docker ps') > 0:
                # find container
                _id = next(line.split()[0] for line in p.stdout
                           if line.split()[-1] == name)

        try:
            os.remove(_batchFile)
        except:
            pass
        finally:
            return _id

    def startOpenFoam(self):
        """Start OpenFOAM for Windows image from batch file."""
        fp = r"C:\Program Files (x86)\ESI\OpenFOAM\v3.0+\Windows\Scripts\start_OF.bat"
        subprocess.Popen(fp, shell=True)

    def header(self):
        """Get header for batch files."""
        if not self.shellinit:
            self.shellinit = self.getShellinit()

        _base = '@echo off\n' \
                'cd "C:\Program Files\Boot2Docker for Windows"\n' \
                'echo Setting up the environment to connect to docker...\n' \
                'echo .\n' \
                '{}\n{}\n{}\n' \
                'echo Done!\n' \
                'echo Running OpenFOAM commands...\n' \
                'echo .'

        return _base.format(*self.shellinit)

    def command(self, cmds, includeHeader=False, log=True):
        """
        Get command line for OpenFOAM commands.
        Args:
            cmds: A sequence of commnads.
        """
        _fp = r"C:\Program Files (x86)\ESI\OpenFOAM\v3.0+\Windows\Scripts\start_OF.bat"
        _msg = "Failed to find container id. Do you have the OpenFOAM container running?\n" + \
            "You can initiate OpenFOAM container by running start_OF.bat:\n" + \
            _fp

        if not self.containerId:
            self.containerId = self.getContainerId()
        assert self.containerId, _msg

        _base = 'docker exec -i {} su - ofuser -c "cd /home/ofuser/workingDir/butterfly/{}; {}"'

        if log:
            _baseCmd = '{0} | tee /home/ofuser/workingDir/butterfly/{1}/etc/{0}.log'
            _cmds = (_baseCmd.format(cmd, self.projectName) for cmd in cmds)
        else:
            _cmds = cmds

        _cmd = _base.format(self.containerId, self.projectName, '; '.join(_cmds))

        if includeHeader:
            return self.header() + "\n" + _cmd
        else:
            return _cmd