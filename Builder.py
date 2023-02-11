"""
 Copyright (C) 2022 Fern Lane, Webinar-hacker
 Licensed under the GNU Affero General Public License, Version 3.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
       https://www.gnu.org/licenses/agpl-3.0.en.html
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR
 OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import platform
import shutil
import subprocess
import sysconfig
import time

from main import WEBINAR_HACKER_VERSION

MAIN_FILE = 'main'
FINAL_NAME = 'Webinar-hacker'

# Text to add to the spec file
SPEC_FILE_HEADER = 'import PyInstaller.config\n' \
                   'PyInstaller.config.CONF[\'workpath\'] = \'./build\'\n'

# Files and folders to include in final build directory (dist/MAIN_FILE folder)
INCLUDE_FILES = ['icon.png',
                 'icon.ico',
                 'gui.ui',
                 'README.md',
                 'LICENSE',
                 'settings.json',
                 'stylesheet',
                 'ffmpeg.exe']

# Files and folders to exclude from final build directory (dist/MAIN_FILE folder)
EXCLUDE_FILES = []

# *.py files to exclude from final build
EXCLUDE_FROM_BUILD = []

if __name__ == '__main__':
    pyi_command = []

    # Remove dist folder is exists
    if 'dist' in os.listdir('./'):
        shutil.rmtree('dist', ignore_errors=True)
        print('dist folder deleted')

    # Remove build folder is exists
    if 'build' in os.listdir('./'):
        shutil.rmtree('build', ignore_errors=True)
        print('build folder deleted')

    # Add all .py files to pyi_command
    for file in os.listdir('./'):
        if file.endswith('.py') and str(file) != MAIN_FILE \
                and str(file) != os.path.basename(__file__) \
                and str(file) not in EXCLUDE_FROM_BUILD:
            pyi_command.append(str(file))

    # Add main file to pyi_command
    pyi_command.insert(0, MAIN_FILE + '.py')

    # Add icon
    pyi_command.insert(0, '--icon=./icon.ico')

    # Other command arguments
    # pyi_command.insert(0, '--windowed')
    pyi_command.insert(0, 'torch')
    pyi_command.insert(0, '--collect-data')

    pyi_command.insert(0, 'tensorflow')
    pyi_command.insert(0, '--collect-data')

    pyi_command.insert(0, 'tensorflow')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'torch')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'tqdm')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'regex')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'packaging')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'requests')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'filelock')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'numpy')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'tokenizers')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'tokenizers')
    pyi_command.insert(0, '--copy-metadata')

    pyi_command.insert(0, 'pyi-makespec')

    # Delete previous spec
    if os.path.exists(MAIN_FILE + '.spec'):
        os.remove(MAIN_FILE + '.spec')

    # Execute pyi
    print(pyi_command)
    subprocess.run(pyi_command, text=True)

    # Spec file generated
    if os.path.exists(MAIN_FILE + '.spec'):
        with open(MAIN_FILE + '.spec', 'r') as spec_file:
            # Read spec file
            spec_data = spec_file.read()
            spec_file.close()

            # Add header to spec file
            spec_data = SPEC_FILE_HEADER + spec_data

            # Disable console
            # spec_data = spec_data.replace('console=True', 'console=False')

            spec_data = spec_data.replace('excludes=[]', 'excludes=[\'torch.distributions\']')
            spec_data = spec_data.replace('hiddenimports=[]',
                                          'hiddenimports=[\'sklearn.metrics\', '
                                          '\'sklearn.metrics._pairwise_distances_reduction._argkmin\', '
                                          '\'sklearn.metrics._pairwise_distances_reduction._base\','
                                          '\'sklearn.metrics._pairwise_distances_reduction._datasets_pair\','
                                          '\'sklearn.metrics._pairwise_distances_reduction._middle_term_computer\','
                                          '\'sklearn.metrics._pairwise_distances_reduction._radius_neighbors\','
                                          '\'sklearn.utils._cython_blas\','
                                          '\'sklearn.neighbors.typedefs\','
                                          '\'sklearn.neighbors.quad_tree\','
                                          '\'sklearn.tree\','
                                          '\'sklearn.tree._utils\','
                                          '\'pytorch\']')

            site_packages_path = sysconfig.get_paths()['purelib']

            spec_data = \
                spec_data.replace('datas = []',
                                  'datas = ['
                                  '(\'' + os.path.join(site_packages_path, 'docx', 'templates').replace('\\', '\\\\') + '\', \'docx/templates\'),'
                                  '(\'' + os.path.join(site_packages_path, 'librosa','util').replace('\\', '\\\\') + '\', \'librosa/util\'),'
                                  '(\'' + os.path.join(site_packages_path,'huggingsound').replace('\\','\\\\') + '\', \'huggingsound\'),'
                                  '(\'' + os.path.join(site_packages_path, 'datasets').replace('\\','\\\\') + '\', \'datasets\'),'
                                  '(\'' + os.path.join(site_packages_path, 'transformers').replace('\\','\\\\') + '\', \'transformers\'),'
                                  '(\'' + 'dict-ru' + '\', \'enchant/data/mingw64/share/enchant/hunspell\')'
                                  ']')

            # Set final name
            spec_data = spec_data.replace('name=\'' + MAIN_FILE + '\'', 'name=\'' + FINAL_NAME + '\'')

            with open(MAIN_FILE + '.spec', 'w') as spec_file_output:
                # Write updated spec file
                spec_file_output.write(spec_data)
                spec_file_output.close()

                # exit(0)

                # Create new pyi command
                # pyi_command = ['pyinstaller', MAIN_FILE + '.spec']
                pyi_command = ['pyinstaller', MAIN_FILE + '.spec', '--clean']

                # Execute pyi
                print(pyi_command)
                subprocess.run(pyi_command, text=True)

                # If dist folder created
                if 'dist' in os.listdir('.') and FINAL_NAME in os.listdir('./dist'):

                    # Remove build folder is exists
                    if 'build' in os.listdir('./'):
                        shutil.rmtree('build', ignore_errors=True)
                        print('build folder deleted')

                    # Wait some time
                    print('Waiting 1 second...')
                    time.sleep(1)

                    # Copy include files to it
                    for file in INCLUDE_FILES:
                        try:
                            if os.path.isfile(file):
                                shutil.copy(file, 'dist/' + FINAL_NAME + '/' + file)
                            elif os.path.isdir(file):
                                shutil.copytree(file, 'dist/' + FINAL_NAME + '/' + file)
                            print('Added', file, 'to dist/', FINAL_NAME, 'folder')
                        except Exception as e:
                            print('Error copying file!', e)

                    # Wait some time
                    print('Waiting 1 second...')
                    time.sleep(1)

                    # Exclude files to it
                    for file in EXCLUDE_FILES:
                        try:
                            if os.path.isfile('dist/' + FINAL_NAME + '/' + file):
                                os.remove('dist/' + FINAL_NAME + '/' + file)
                            elif os.path.isdir('dist/' + FINAL_NAME + '/' + file):
                                shutil.rmtree('dist/' + FINAL_NAME + '/' + file)
                            print('Removed', file, 'from dist/', FINAL_NAME, 'folder')
                        except Exception as e:
                            print('Error excluding file!', e)

                    # Wait some time
                    print('Waiting 1 second...')
                    time.sleep(1)

                    # Rename final folder
                    os.rename('dist/' + FINAL_NAME, 'dist/' + FINAL_NAME + '-' + WEBINAR_HACKER_VERSION
                              + '-' + str(platform.system() + '-' + str(platform.machine())))

                else:
                    print('Error. No dist/' + FINAL_NAME + ' folder!')

    # Spec file not generated
    else:
        print('Error generating spec!')
