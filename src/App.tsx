/**
 * New Layout
 */
import "./App.css";
import "@aws-amplify/ui-react/styles.css";

import { Box, Tab, Tabs, Typography } from "@mui/material";
import React, { useState } from "react";

import ASL2EnglishForm from "./components/ASL2EnglishForm.tsx";
import ASLForm from "./components/ASLForm.tsx";
import ImageName from "./assets/gen-asl-logo.png";
import styled from "styled-components";

// import VideoComponent from './components/VideoComponent.tsx';

const Page = styled.div`
  width: 100vw;
  height: 100%;
  min-height: 100%;
  box-sizing: border-box;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 2rem;
`;

function App() {
  const [currentTabIndex, setCurrentTabIndex] = useState(0);

  const handleTabChange = (_e: any, tabIndex: React.SetStateAction<number>) => {
    setCurrentTabIndex(tabIndex);
  };


  return (


    <div id="App-Container" className="main-container">
      <div id="App-Header" className="main-container-header">
        <table id="App-Header-Table">
          <tbody>
            <tr id="Header-Table-Row1">
              <td>
                <div className="gen-asl-logo">
                  <img src={ImageName} alt="gen-asl-logo" />
                </div>
              </td>
              <td>Generative AI Application To Translate English to Sign Languages</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div id="App-Content">
        <Page id="App-Content-Page">
          <div id="App-Content-TabContainer">
            <Tabs
              value={currentTabIndex}
              onChange={handleTabChange}
              indicatorColor="secondary"
              textColor="secondary"
              orientation="vertical"
            >
              <Tab id="App-Content-TabSelector-ENG2ASL" label={<Typography variant="h4">English To ASL</Typography>} />
              <Tab id="App-Content-TabSelector-ASL2ENG" label={<Typography variant="h4">ASL to English</Typography>} />
            </Tabs>
          </div>
          <div id="App-Content-TabPanel" style={{ width: "90%" }}>
            {currentTabIndex === 0 && (
              <Box id="App-Content-Box-ENG2ASL" sx={{ p: 3 }}>
                <div>{<ASLForm />}</div>
              </Box>
            )}

            {currentTabIndex === 1 && (
              <Box id="App-Content-Box-ASL2ENG" sx={{ p: 3 }}>
                <div>
                  {<ASL2EnglishForm/>}
                </div>
              </Box>
            )}
          </div>
        </Page>
      </div>
    </div>
  );
}

export default App;
